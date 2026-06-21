from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import AppError, NotFoundError
from app.models.entities import Payment, PaymentStatus, User
from app.models.enums import PaymentAction, PaymentProvider, VALID_BILLING_MONTHS
from app.schemas.admin import PaymentCheckoutPreviewResponse
from app.services.company_offer_service import (
    get_active_company_subscription_offer,
    resolve_company_checkout_amount,
)
from app.services.payment_providers.factory import get_payment_provider
from app.services.plan_pricing_service import (
    apply_checkout_discounts,
    build_plan_response,
    resolve_checkout_company_id,
)
from app.services.promo_service import (
    _validate_checkout_params,
    register_promo_usage,
    resolve_promo_for_checkout,
)
from app.services.promotion_service import (
    register_promotion_usage,
    resolve_best_promotion_for_checkout,
)
from app.services.subscription_service import (
    calculate_price,
    change_plan,
    create_subscription_from_payment,
    get_subscription_by_id,
    renew_subscription,
)


async def preview_checkout(
    db: AsyncSession,
    user: User,
    plan_code: str,
    action: PaymentAction,
    period_months: int,
    subscription_id: UUID | None = None,
    promo_code: str | None = None,
) -> PaymentCheckoutPreviewResponse:
    plan = await _validate_checkout_params(
        db, user, plan_code, action, period_months, subscription_id
    )
    company_id = await resolve_checkout_company_id(db, user, action, subscription_id)
    standard_amount = calculate_price(plan, period_months)
    custom_offer = await get_active_company_subscription_offer(db, company_id) if company_id else None

    if custom_offer:
        offer_amount, _ = await resolve_company_checkout_amount(
            db,
            company_id=company_id,
            plan=plan,
            period_months=period_months,
        )
        return PaymentCheckoutPreviewResponse(
            plan=build_plan_response(plan, None),
            action=action,
            period_months=period_months,
            original_amount=standard_amount,
            discount_amount=standard_amount - offer_amount,
            amount=offer_amount,
            promo_code=None,
            promo_applied=False,
            promo_error=None,
            promotion_id=None,
            promotion_name=None,
            promotion_applied=False,
            custom_offer_applied=True,
            custom_offer_name=custom_offer.display_name or custom_offer.name,
        )

    original_amount = standard_amount
    promotion = await resolve_best_promotion_for_checkout(
        db,
        plan=plan,
        action=action,
        period_months=period_months,
        company_id=company_id,
    )

    promo_discount_percent: int | None = None
    promo_applied = False
    promo_error: str | None = None
    applied_code: str | None = None

    if promo_code:
        try:
            promo = await resolve_promo_for_checkout(
                db,
                promo_code=promo_code,
                user=user,
                plan=plan,
                action=action,
            )
            promo_discount_percent = promo.discount_percent
            applied_code = promo.code
        except AppError as exc:
            promo_error = exc.message

    final_amount, discount_amount, applied_promotion, promo_wins = apply_checkout_discounts(
        original_amount,
        promotion=promotion,
        plan=plan,
        promo_discount_percent=promo_discount_percent,
    )
    promo_applied = promo_wins and promo_discount_percent is not None

    chosen = applied_promotion or promotion
    plan_response = build_plan_response(plan, [chosen] if chosen else None)

    return PaymentCheckoutPreviewResponse(
        plan=plan_response,
        action=action,
        period_months=period_months,
        original_amount=original_amount,
        discount_amount=discount_amount,
        amount=final_amount,
        promo_code=applied_code if promo_applied else None,
        promo_applied=promo_applied,
        promo_error=promo_error,
        promotion_id=applied_promotion.id if applied_promotion else None,
        promotion_name=applied_promotion.name if applied_promotion else None,
        promotion_applied=applied_promotion is not None,
        custom_offer_applied=False,
        custom_offer_name=None,
    )


async def create_checkout(
    db: AsyncSession,
    user: User,
    plan_code: str,
    action: PaymentAction,
    period_months: int,
    subscription_id: UUID | None = None,
    promo_code: str | None = None,
) -> Payment:
    if period_months not in VALID_BILLING_MONTHS:
        raise AppError("Период оплаты: 1, 3, 6 или 12 месяцев")

    plan = await _validate_checkout_params(
        db, user, plan_code, action, period_months, subscription_id
    )
    company_id = await resolve_checkout_company_id(db, user, action, subscription_id)
    standard_amount = calculate_price(plan, period_months)
    custom_offer = await get_active_company_subscription_offer(db, company_id) if company_id else None

    if custom_offer:
        offer_amount, _ = await resolve_company_checkout_amount(
            db,
            company_id=company_id,
            plan=plan,
            period_months=period_months,
        )
        payment = Payment(
            user_id=user.id,
            plan_id=plan.id,
            user_subscription_id=subscription_id,
            action=action,
            period_months=period_months,
            provider=PaymentProvider(settings.payment_provider),
            original_amount=standard_amount,
            discount_amount=standard_amount - offer_amount,
            amount=offer_amount,
            promo_code_id=None,
            subscription_promotion_id=None,
            currency="RUB",
            status=PaymentStatus.PENDING,
        )
        db.add(payment)
        await db.flush()
        provider = get_payment_provider()
        description = (
            f"Подписка {plan.name} ({period_months} мес.), "
            f"индивидуальное предложение «{custom_offer.display_name or custom_offer.name}»"
        )
        checkout = await provider.create_checkout(
            payment_id=payment.id,
            amount=payment.amount,
            currency=payment.currency,
            description=description,
            return_url=settings.payment_return_url,
        )
        payment.provider_payment_id = checkout.provider_payment_id
        payment.confirmation_url = checkout.confirmation_url
        payment.provider_metadata = checkout.metadata
        await db.flush()
        if PaymentProvider(settings.payment_provider) == PaymentProvider.MOCK:
            await complete_payment(db, payment.id)
        await db.refresh(payment, ["plan", "promo_code", "subscription_promotion"])
        return payment

    original_amount = standard_amount
    promotion = await resolve_best_promotion_for_checkout(
        db,
        plan=plan,
        action=action,
        period_months=period_months,
        company_id=company_id,
    )

    promo_discount_percent: int | None = None
    promo_id: UUID | None = None

    if promo_code:
        promo = await resolve_promo_for_checkout(
            db,
            promo_code=promo_code,
            user=user,
            plan=plan,
            action=action,
        )
        promo_discount_percent = promo.discount_percent
        promo_id = promo.id

    final_amount, discount_amount, applied_promotion, promo_wins = apply_checkout_discounts(
        original_amount,
        promotion=promotion,
        plan=plan,
        promo_discount_percent=promo_discount_percent,
    )
    if promo_wins:
        promotion_id = None
    else:
        promotion_id = applied_promotion.id if applied_promotion else None
        promo_id = None

    payment = Payment(
        user_id=user.id,
        plan_id=plan.id,
        user_subscription_id=subscription_id,
        action=action,
        period_months=period_months,
        provider=PaymentProvider(settings.payment_provider),
        original_amount=original_amount,
        discount_amount=discount_amount,
        amount=final_amount,
        promo_code_id=promo_id,
        subscription_promotion_id=promotion_id,
        currency="RUB",
        status=PaymentStatus.PENDING,
    )
    db.add(payment)
    await db.flush()

    provider = get_payment_provider()
    description = f"Подписка {plan.name} ({period_months} мес.)"
    if discount_amount:
        description += f", скидка {discount_amount} ₽"

    checkout = await provider.create_checkout(
        payment_id=payment.id,
        amount=payment.amount,
        currency=payment.currency,
        description=description,
        return_url=settings.payment_return_url,
    )
    payment.provider_payment_id = checkout.provider_payment_id
    payment.confirmation_url = checkout.confirmation_url
    payment.provider_metadata = checkout.metadata
    await db.flush()

    if PaymentProvider(settings.payment_provider) == PaymentProvider.MOCK:
        await complete_payment(db, payment.id)

    await db.refresh(payment, ["plan", "promo_code", "subscription_promotion"])
    return payment


async def get_payment(db: AsyncSession, payment_id: UUID, user_id: UUID) -> Payment:
    result = await db.execute(
        select(Payment)
        .options(
            selectinload(Payment.plan),
            selectinload(Payment.promo_code),
            selectinload(Payment.subscription_promotion),
        )
        .where(Payment.id == payment_id, Payment.user_id == user_id)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise NotFoundError("Платёж не найден")
    return payment


async def complete_payment(db: AsyncSession, payment_id: UUID) -> Payment:
    result = await db.execute(
        select(Payment)
        .options(
            selectinload(Payment.plan),
            selectinload(Payment.promo_code),
            selectinload(Payment.subscription_promotion),
        )
        .where(Payment.id == payment_id)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise NotFoundError("Платёж не найден")

    if payment.status == PaymentStatus.SUCCEEDED:
        return payment

    payment.status = PaymentStatus.SUCCEEDED
    payment.paid_at = datetime.now(UTC)
    await _apply_payment(db, payment)
    await register_promo_usage(db, payment)
    await register_promotion_usage(db, payment)
    await db.flush()
    await db.refresh(payment, ["plan", "promo_code", "subscription_promotion"])
    return payment


async def process_webhook(
    db: AsyncSession, provider: PaymentProvider, payload: dict[str, Any]
) -> Payment | None:
    gateway = get_payment_provider()
    provider_payment_id, status = await gateway.parse_webhook(payload)

    result = await db.execute(
        select(Payment)
        .options(selectinload(Payment.plan))
        .where(Payment.provider == provider, Payment.provider_payment_id == provider_payment_id)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        return None

    if status in ("succeeded", "paid", "success"):
        return await complete_payment(db, payment.id)
    if status in ("canceled", "cancelled"):
        payment.status = PaymentStatus.CANCELLED
        await db.flush()
    elif status in ("failed",):
        payment.status = PaymentStatus.FAILED
        await db.flush()

    return payment


async def _apply_payment(db: AsyncSession, payment: Payment) -> None:
    user = await db.get(User, payment.user_id)
    if not user:
        raise NotFoundError("Пользователь не найден")

    if payment.action == PaymentAction.PURCHASE:
        await create_subscription_from_payment(
            db, user, payment.plan, payment.period_months, payment.id
        )
    elif payment.action == PaymentAction.RENEW:
        if not payment.user_subscription_id:
            raise AppError("subscription_id обязателен для продления")
        subscription = await get_subscription_by_id(db, payment.user_subscription_id, user.id)
        await renew_subscription(db, subscription, payment.period_months, payment.id)
    elif payment.action == PaymentAction.CHANGE_PLAN:
        if not payment.user_subscription_id:
            raise AppError("subscription_id обязателен для смены тарифа")
        subscription = await get_subscription_by_id(db, payment.user_subscription_id, user.id)
        old_plan = subscription.plan
        await change_plan(db, subscription, payment.plan, payment.id)
        from app.services.subscription_service import is_upgrade

        if is_upgrade(old_plan, payment.plan):
            await renew_subscription(db, subscription, payment.period_months, payment.id)
