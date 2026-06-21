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
from app.services.company_service import get_plan_by_code
from app.services.payment_providers.factory import get_payment_provider
from app.services.promo_service import (
    _validate_checkout_params,
    calculate_discount,
    register_promo_usage,
    resolve_promo_for_checkout,
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
    original_amount = calculate_price(plan, period_months)
    discount_amount = 0
    final_amount = original_amount
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
            final_amount, discount_amount = calculate_discount(original_amount, promo.discount_percent)
            promo_applied = True
            applied_code = promo.code
        except AppError as exc:
            promo_error = exc.message

    from app.schemas.schemas import SubscriptionPlanResponse

    return PaymentCheckoutPreviewResponse(
        plan=SubscriptionPlanResponse.model_validate(plan),
        action=action,
        period_months=period_months,
        original_amount=original_amount,
        discount_amount=discount_amount,
        amount=final_amount,
        promo_code=applied_code,
        promo_applied=promo_applied,
        promo_error=promo_error,
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
    original_amount = calculate_price(plan, period_months)
    discount_amount = 0
    final_amount = original_amount
    promo_id: UUID | None = None

    if promo_code:
        promo = await resolve_promo_for_checkout(
            db,
            promo_code=promo_code,
            user=user,
            plan=plan,
            action=action,
        )
        final_amount, discount_amount = calculate_discount(original_amount, promo.discount_percent)
        promo_id = promo.id

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

    await db.refresh(payment, ["plan", "promo_code"])
    return payment


async def get_payment(db: AsyncSession, payment_id: UUID, user_id: UUID) -> Payment:
    result = await db.execute(
        select(Payment)
        .options(selectinload(Payment.plan), selectinload(Payment.promo_code))
        .where(Payment.id == payment_id, Payment.user_id == user_id)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise NotFoundError("Платёж не найден")
    return payment


async def complete_payment(db: AsyncSession, payment_id: UUID) -> Payment:
    result = await db.execute(
        select(Payment)
        .options(selectinload(Payment.plan), selectinload(Payment.promo_code))
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
    await db.flush()
    await db.refresh(payment, ["plan", "promo_code"])
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
