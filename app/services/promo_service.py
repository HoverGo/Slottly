from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.models.entities import Payment, PromoCode, SubscriptionPlan, User
from app.models.enums import PaymentAction
from app.services.company_service import get_plan_by_code
from app.services.subscription_service import get_subscription_by_id, validate_plan_for_company


def normalize_promo_code(code: str) -> str:
    return code.strip().upper()


def calculate_discount(original_amount: int, discount_percent: int) -> tuple[int, int]:
    if discount_percent < 1 or discount_percent > 100:
        raise AppError("Скидка промокода: от 1 до 100%")
    discount_amount = original_amount * discount_percent // 100
    final_amount = max(original_amount - discount_amount, 0)
    return final_amount, discount_amount


async def get_promo_by_code(db: AsyncSession, code: str) -> PromoCode | None:
    normalized = normalize_promo_code(code)
    result = await db.execute(select(PromoCode).where(PromoCode.code == normalized))
    return result.scalar_one_or_none()


async def validate_promo_for_checkout(
    db: AsyncSession,
    promo: PromoCode,
    *,
    user: User,
    plan: SubscriptionPlan,
    action: PaymentAction,
) -> None:
    if not promo.is_active:
        raise AppError("Промокод неактивен")

    now = datetime.now(UTC)
    if promo.valid_from and now < promo.valid_from:
        raise AppError("Промокод ещё не действует")
    if promo.valid_until and now > promo.valid_until:
        raise AppError("Срок действия промокода истёк")

    if promo.user_id and promo.user_id != user.id:
        raise AppError("Промокод недоступен для вашего аккаунта")

    if promo.plan_codes and plan.code not in promo.plan_codes:
        raise AppError("Промокод не применим к выбранному тарифу")

    if promo.actions and action.value not in promo.actions:
        raise AppError("Промокод не применим к этому типу оплаты")

    if promo.max_uses is not None and promo.used_count >= promo.max_uses:
        raise AppError("Лимит использований промокода исчерпан")


async def resolve_promo_for_checkout(
    db: AsyncSession,
    *,
    promo_code: str,
    user: User,
    plan: SubscriptionPlan,
    action: PaymentAction,
) -> PromoCode:
    promo = await get_promo_by_code(db, promo_code)
    if not promo:
        raise AppError("Промокод не найден")
    await validate_promo_for_checkout(db, promo, user=user, plan=plan, action=action)
    return promo


async def register_promo_usage(db: AsyncSession, payment: Payment) -> None:
    if not payment.promo_code_id:
        return

    promo = await db.get(PromoCode, payment.promo_code_id)
    if promo:
        promo.used_count += 1
        await db.flush()


async def create_promo_code(
    db: AsyncSession,
    admin: User,
    *,
    code: str,
    discount_percent: int,
    user_id: UUID | None = None,
    plan_codes: list[str] | None = None,
    actions: list[str] | None = None,
    max_uses: int | None = None,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
    description: str | None = None,
) -> PromoCode:
    normalized = normalize_promo_code(code)
    if not normalized:
        raise AppError("Код промокода не может быть пустым")

    existing = await get_promo_by_code(db, normalized)
    if existing:
        raise ConflictError("Промокод с таким кодом уже существует")

    if user_id:
        target = await db.get(User, user_id)
        if not target:
            raise NotFoundError("Пользователь для персонального промокода не найден")
        if max_uses is None:
            max_uses = 1

    if plan_codes:
        for plan_code in plan_codes:
            await get_plan_by_code(db, plan_code)

    if actions:
        valid_actions = {a.value for a in PaymentAction}
        invalid = set(actions) - valid_actions
        if invalid:
            raise AppError(f"Неизвестные типы оплаты: {', '.join(sorted(invalid))}")

    promo = PromoCode(
        code=normalized,
        discount_percent=discount_percent,
        user_id=user_id,
        plan_codes=plan_codes,
        actions=actions,
        max_uses=max_uses,
        valid_from=valid_from,
        valid_until=valid_until,
        description=description,
        created_by_id=admin.id,
    )
    db.add(promo)
    await db.flush()
    return promo


async def list_promo_codes(db: AsyncSession) -> list[PromoCode]:
    result = await db.execute(
        select(PromoCode)
        .options(selectinload(PromoCode.user))
        .order_by(PromoCode.created_at.desc())
    )
    return list(result.scalars().all())


async def update_promo_code(
    db: AsyncSession,
    promo_id: UUID,
    *,
    discount_percent: int | None = None,
    plan_codes: list[str] | None = None,
    actions: list[str] | None = None,
    max_uses: int | None = None,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
    is_active: bool | None = None,
    description: str | None = None,
    clear_valid_from: bool = False,
    clear_valid_until: bool = False,
) -> PromoCode:
    promo = await db.get(PromoCode, promo_id)
    if not promo:
        raise NotFoundError("Промокод не найден")

    if discount_percent is not None:
        if discount_percent < 1 or discount_percent > 100:
            raise AppError("Скидка: от 1 до 100%")
        promo.discount_percent = discount_percent

    if plan_codes is not None:
        for plan_code in plan_codes:
            await get_plan_by_code(db, plan_code)
        promo.plan_codes = plan_codes or None

    if actions is not None:
        valid_actions = {a.value for a in PaymentAction}
        invalid = set(actions) - valid_actions
        if invalid:
            raise AppError(f"Неизвестные типы оплаты: {', '.join(sorted(invalid))}")
        promo.actions = actions or None

    if max_uses is not None:
        promo.max_uses = max_uses

    if clear_valid_from:
        promo.valid_from = None
    elif valid_from is not None:
        promo.valid_from = valid_from

    if clear_valid_until:
        promo.valid_until = None
    elif valid_until is not None:
        promo.valid_until = valid_until

    if is_active is not None:
        promo.is_active = is_active

    if description is not None:
        promo.description = description

    await db.flush()
    return promo


async def _validate_checkout_params(
    db: AsyncSession,
    user: User,
    plan_code: str,
    action: PaymentAction,
    period_months: int,
    subscription_id: UUID | None,
) -> SubscriptionPlan:
    from app.models.enums import VALID_BILLING_MONTHS

    if period_months not in VALID_BILLING_MONTHS:
        raise AppError("Период оплаты: 1, 3, 6 или 12 месяцев")

    plan = await get_plan_by_code(db, plan_code)

    if action == PaymentAction.PURCHASE:
        pass
    elif action in (PaymentAction.RENEW, PaymentAction.CHANGE_PLAN):
        if not subscription_id:
            raise AppError("Укажите subscription_id")
        subscription = await get_subscription_by_id(db, subscription_id, user.id)
        if action == PaymentAction.CHANGE_PLAN and subscription.company_id:
            await validate_plan_for_company(db, subscription.company_id, plan)
    else:
        raise AppError("Неизвестный тип оплаты")

    return plan
