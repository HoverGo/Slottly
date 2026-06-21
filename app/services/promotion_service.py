from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.models.entities import (
    Payment,
    PaymentStatus,
    SubscriptionPlan,
    SubscriptionPromotion,
    User,
    UserSubscription,
)
from app.models.enums import PaymentAction
from app.services.company_service import get_plan_by_code
from app.services.promo_service import calculate_discount


async def company_had_successful_plan_payment(
    db: AsyncSession, company_id: UUID, plan_id: UUID
) -> bool:
    count = await db.scalar(
        select(func.count())
        .select_from(Payment)
        .join(
            UserSubscription,
            or_(
                UserSubscription.id == Payment.user_subscription_id,
                UserSubscription.payment_id == Payment.id,
            ),
        )
        .where(
            Payment.status == PaymentStatus.SUCCEEDED,
            Payment.plan_id == plan_id,
            UserSubscription.company_id == company_id,
        )
    )
    return (count or 0) > 0


def _promotion_matches_company(promotion: SubscriptionPromotion, company_id: UUID | None) -> bool:
    if promotion.for_all_companies:
        return True
    if company_id is None:
        return False
    if not promotion.company_ids:
        return False
    return str(company_id) in promotion.company_ids


async def _promotion_matches_first_purchase(
    db: AsyncSession,
    promotion: SubscriptionPromotion,
    *,
    company_id: UUID | None,
    plan_id: UUID,
) -> bool:
    if not promotion.first_plan_purchase_only:
        return True
    if company_id is None:
        return True
    return not await company_had_successful_plan_payment(db, company_id, plan_id)


def _promotion_is_active_now(promotion: SubscriptionPromotion) -> bool:
    if not promotion.is_active:
        return False
    now = datetime.now(UTC)
    if promotion.valid_from and now < promotion.valid_from:
        return False
    if promotion.valid_until and now > promotion.valid_until:
        return False
    if promotion.max_uses is not None and promotion.used_count >= promotion.max_uses:
        return False
    return True


async def validate_promotion_for_checkout(
    db: AsyncSession,
    promotion: SubscriptionPromotion,
    *,
    plan: SubscriptionPlan,
    action: PaymentAction,
    company_id: UUID | None,
) -> None:
    if not _promotion_is_active_now(promotion):
        raise AppError("Акция неактивна или недоступна")

    if promotion.plan_codes and plan.code not in promotion.plan_codes:
        raise AppError("Акция не применима к выбранному тарифу")

    if promotion.actions and action.value not in promotion.actions:
        raise AppError("Акция не применима к этому типу оплаты")

    if not _promotion_matches_company(promotion, company_id):
        raise AppError("Акция недоступна для этой организации")

    if not await _promotion_matches_first_purchase(
        db, promotion, company_id=company_id, plan_id=plan.id
    ):
        raise AppError("Акция только для первой покупки этого тарифа у организации")


async def list_active_promotions(db: AsyncSession) -> list[SubscriptionPromotion]:
    result = await db.execute(
        select(SubscriptionPromotion)
        .where(SubscriptionPromotion.is_active.is_(True))
        .order_by(SubscriptionPromotion.discount_percent.desc(), SubscriptionPromotion.created_at.desc())
    )
    return [item for item in result.scalars().all() if _promotion_is_active_now(item)]


async def resolve_best_promotion_for_checkout(
    db: AsyncSession,
    *,
    plan: SubscriptionPlan,
    action: PaymentAction,
    company_id: UUID | None,
) -> SubscriptionPromotion | None:
    promotions = await list_active_promotions(db)
    eligible: list[SubscriptionPromotion] = []
    for promotion in promotions:
        try:
            await validate_promotion_for_checkout(
                db, promotion, plan=plan, action=action, company_id=company_id
            )
            eligible.append(promotion)
        except AppError:
            continue
    if not eligible:
        return None
    return max(eligible, key=lambda item: (item.discount_percent, item.created_at))


async def resolve_best_promotion_for_plan_display(
    db: AsyncSession,
    *,
    plan: SubscriptionPlan,
    company_id: UUID | None = None,
) -> SubscriptionPromotion | None:
    return await resolve_best_promotion_for_checkout(
        db,
        plan=plan,
        action=PaymentAction.PURCHASE,
        company_id=company_id,
    )


def promotion_discounted_monthly_price(plan: SubscriptionPlan, promotion: SubscriptionPromotion) -> int:
    final_amount, _ = calculate_discount(plan.price_monthly, promotion.discount_percent)
    return final_amount


async def register_promotion_usage(db: AsyncSession, payment: Payment) -> None:
    if not payment.subscription_promotion_id:
        return
    promotion = await db.get(SubscriptionPromotion, payment.subscription_promotion_id)
    if promotion:
        promotion.used_count += 1
        await db.flush()


async def create_subscription_promotion(
    db: AsyncSession,
    admin: User,
    *,
    name: str,
    discount_percent: int,
    plan_codes: list[str] | None = None,
    actions: list[str] | None = None,
    for_all_companies: bool = True,
    company_ids: list[UUID] | None = None,
    first_plan_purchase_only: bool = False,
    max_uses: int | None = None,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
    description: str | None = None,
) -> SubscriptionPromotion:
    title = name.strip()
    if not title:
        raise AppError("Название акции не может быть пустым")
    if discount_percent < 1 or discount_percent > 100:
        raise AppError("Скидка: от 1 до 100%")

    if plan_codes:
        for plan_code in plan_codes:
            await get_plan_by_code(db, plan_code)

    if actions:
        valid_actions = {a.value for a in PaymentAction}
        invalid = set(actions) - valid_actions
        if invalid:
            raise AppError(f"Неизвестные типы оплаты: {', '.join(sorted(invalid))}")

    if not for_all_companies:
        if not company_ids:
            raise AppError("Укажите company_ids или включите for_all_companies")
        for company_id in company_ids:
            from app.models.entities import Company

            company = await db.get(Company, company_id)
            if not company:
                raise NotFoundError(f"Компания {company_id} не найдена")

    promotion = SubscriptionPromotion(
        name=title,
        discount_percent=discount_percent,
        plan_codes=plan_codes,
        actions=actions,
        for_all_companies=for_all_companies,
        company_ids=[str(item) for item in company_ids] if company_ids else None,
        first_plan_purchase_only=first_plan_purchase_only,
        max_uses=max_uses,
        valid_from=valid_from,
        valid_until=valid_until,
        description=description,
        created_by_id=admin.id,
    )
    db.add(promotion)
    await db.flush()
    return promotion


async def list_subscription_promotions(db: AsyncSession) -> list[SubscriptionPromotion]:
    result = await db.execute(
        select(SubscriptionPromotion).order_by(SubscriptionPromotion.created_at.desc())
    )
    return list(result.scalars().all())


async def update_subscription_promotion(
    db: AsyncSession,
    promotion_id: UUID,
    *,
    name: str | None = None,
    discount_percent: int | None = None,
    plan_codes: list[str] | None = None,
    actions: list[str] | None = None,
    for_all_companies: bool | None = None,
    company_ids: list[UUID] | None = None,
    first_plan_purchase_only: bool | None = None,
    max_uses: int | None = None,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
    clear_valid_from: bool = False,
    clear_valid_until: bool = False,
    is_active: bool | None = None,
    description: str | None = None,
    clear_company_ids: bool = False,
) -> SubscriptionPromotion:
    promotion = await db.get(SubscriptionPromotion, promotion_id)
    if not promotion:
        raise NotFoundError("Акция не найдена")

    if name is not None:
        title = name.strip()
        if not title:
            raise AppError("Название акции не может быть пустым")
        promotion.name = title

    if discount_percent is not None:
        if discount_percent < 1 or discount_percent > 100:
            raise AppError("Скидка: от 1 до 100%")
        promotion.discount_percent = discount_percent

    if plan_codes is not None:
        for plan_code in plan_codes:
            await get_plan_by_code(db, plan_code)
        promotion.plan_codes = plan_codes or None

    if actions is not None:
        valid_actions = {a.value for a in PaymentAction}
        invalid = set(actions) - valid_actions
        if invalid:
            raise AppError(f"Неизвестные типы оплаты: {', '.join(sorted(invalid))}")
        promotion.actions = actions or None

    if for_all_companies is not None:
        promotion.for_all_companies = for_all_companies
        if for_all_companies:
            promotion.company_ids = None

    if clear_company_ids:
        promotion.company_ids = None
    elif company_ids is not None:
        for company_id in company_ids:
            from app.models.entities import Company

            company = await db.get(Company, company_id)
            if not company:
                raise NotFoundError(f"Компания {company_id} не найдена")
        promotion.company_ids = [str(item) for item in company_ids]
        promotion.for_all_companies = False

    if first_plan_purchase_only is not None:
        promotion.first_plan_purchase_only = first_plan_purchase_only

    if max_uses is not None:
        promotion.max_uses = max_uses

    if clear_valid_from:
        promotion.valid_from = None
    elif valid_from is not None:
        promotion.valid_from = valid_from

    if clear_valid_until:
        promotion.valid_until = None
    elif valid_until is not None:
        promotion.valid_until = valid_until

    if is_active is not None:
        promotion.is_active = is_active

    if description is not None:
        promotion.description = description

    if not promotion.for_all_companies and not promotion.company_ids:
        raise ConflictError("Укажите company_ids или включите for_all_companies")

    await db.flush()
    return promotion
