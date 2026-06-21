from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
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
from app.models.enums import PaymentAction, VALID_BILLING_MONTHS
from app.services.company_service import get_plan_by_code
from app.services.subscription_service import calculate_price


async def company_had_any_successful_payment(db: AsyncSession, company_id: UUID) -> bool:
    count = await db.scalar(
        select(func.count())
        .select_from(Payment)
        .join(UserSubscription, UserSubscription.id == Payment.user_subscription_id)
        .where(
            Payment.status == PaymentStatus.SUCCEEDED,
            UserSubscription.company_id == company_id,
        )
    )
    if (count or 0) > 0:
        return True

    initial_count = await db.scalar(
        select(func.count())
        .select_from(Payment)
        .join(UserSubscription, UserSubscription.payment_id == Payment.id)
        .where(
            Payment.status == PaymentStatus.SUCCEEDED,
            UserSubscription.company_id == company_id,
        )
    )
    return (initial_count or 0) > 0


def _promotion_matches_company(promotion: SubscriptionPromotion, company_id: UUID | None) -> bool:
    if promotion.for_all_companies:
        return True
    if company_id is None:
        return False
    if not promotion.company_ids:
        return False
    return str(company_id) in promotion.company_ids


async def _promotion_matches_new_company(
    db: AsyncSession,
    promotion: SubscriptionPromotion,
    *,
    company_id: UUID | None,
) -> bool:
    if not promotion.new_companies_only:
        return True
    if company_id is None:
        return True
    return not await company_had_any_successful_payment(db, company_id)


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


def promotion_base_amount(plan: SubscriptionPlan, promotion: SubscriptionPromotion) -> int:
    return calculate_price(plan, promotion.period_months)


async def validate_promotion_for_checkout(
    db: AsyncSession,
    promotion: SubscriptionPromotion,
    *,
    plan: SubscriptionPlan,
    action: PaymentAction,
    period_months: int,
    company_id: UUID | None,
) -> None:
    if action != PaymentAction.PURCHASE:
        raise AppError("Акция применима только к покупке подписки")

    if not _promotion_is_active_now(promotion):
        raise AppError("Акция неактивна или недоступна")

    if promotion.plan_code != plan.code:
        raise AppError("Акция не применима к выбранному тарифу")

    if promotion.period_months != period_months:
        raise AppError("Акция не применима к выбранному сроку оплаты")

    if not _promotion_matches_company(promotion, company_id):
        raise AppError("Акция недоступна для этой организации")

    if not await _promotion_matches_new_company(db, promotion, company_id=company_id):
        raise AppError("Акция только для новых компаний")

    base_amount = promotion_base_amount(plan, promotion)
    if promotion.promotional_amount >= base_amount:
        raise AppError("Стоимость акции должна быть ниже базовой")


async def list_active_promotions(db: AsyncSession) -> list[SubscriptionPromotion]:
    result = await db.execute(
        select(SubscriptionPromotion)
        .where(SubscriptionPromotion.is_active.is_(True))
        .order_by(SubscriptionPromotion.created_at.desc())
    )
    return [item for item in result.scalars().all() if _promotion_is_active_now(item)]


async def list_eligible_promotions(
    db: AsyncSession,
    *,
    plan: SubscriptionPlan,
    action: PaymentAction,
    period_months: int,
    company_id: UUID | None,
) -> list[SubscriptionPromotion]:
    promotions = await list_active_promotions(db)
    eligible: list[SubscriptionPromotion] = []
    for promotion in promotions:
        try:
            await validate_promotion_for_checkout(
                db,
                promotion,
                plan=plan,
                action=action,
                period_months=period_months,
                company_id=company_id,
            )
            eligible.append(promotion)
        except AppError:
            continue
    return eligible


async def resolve_best_promotion_for_checkout(
    db: AsyncSession,
    *,
    plan: SubscriptionPlan,
    action: PaymentAction,
    period_months: int,
    company_id: UUID | None,
) -> SubscriptionPromotion | None:
    eligible = await list_eligible_promotions(
        db,
        plan=plan,
        action=action,
        period_months=period_months,
        company_id=company_id,
    )
    if not eligible:
        return None
    return min(eligible, key=lambda item: (item.promotional_amount, item.created_at))


async def list_eligible_promotions_for_plan_display(
    db: AsyncSession,
    *,
    plan: SubscriptionPlan,
    company_id: UUID | None = None,
) -> list[SubscriptionPromotion]:
    result: list[SubscriptionPromotion] = []
    for period_months in VALID_BILLING_MONTHS:
        promotion = await resolve_best_promotion_for_checkout(
            db,
            plan=plan,
            action=PaymentAction.PURCHASE,
            period_months=period_months,
            company_id=company_id,
        )
        if promotion:
            result.append(promotion)
    return result


def promotion_discounted_monthly_price(plan: SubscriptionPlan, promotion: SubscriptionPromotion) -> int:
    if promotion.period_months == 1:
        return promotion.promotional_amount
    return promotion.promotional_amount // promotion.period_months


def promotion_checkout_amounts(
    plan: SubscriptionPlan, promotion: SubscriptionPromotion
) -> tuple[int, int]:
    original_amount = promotion_base_amount(plan, promotion)
    final_amount = promotion.promotional_amount
    discount_amount = original_amount - final_amount
    return final_amount, discount_amount


async def register_promotion_usage(db: AsyncSession, payment: Payment) -> None:
    if not payment.subscription_promotion_id:
        return
    promotion = await db.get(SubscriptionPromotion, payment.subscription_promotion_id)
    if promotion:
        promotion.used_count += 1
        await db.flush()


async def _validate_promotional_price(
    db: AsyncSession,
    *,
    plan_code: str,
    period_months: int,
    promotional_amount: int,
) -> SubscriptionPlan:
    if period_months not in VALID_BILLING_MONTHS:
        raise AppError("Срок акции: 1, 3, 6 или 12 месяцев")
    plan = await get_plan_by_code(db, plan_code)
    base_amount = calculate_price(plan, period_months)
    if promotional_amount >= base_amount:
        raise AppError(
            f"Стоимость акции ({promotional_amount} ₽) должна быть ниже базовой ({base_amount} ₽)"
        )
    if promotional_amount < 1:
        raise AppError("Стоимость акции должна быть больше 0")
    return plan


async def load_promotion_companies(
    db: AsyncSession, promotion: SubscriptionPromotion
) -> list[dict]:
    if promotion.for_all_companies or not promotion.company_ids:
        return []
    from app.models.entities import Company

    ids = [UUID(item) for item in promotion.company_ids]
    result = await db.execute(select(Company.id, Company.name).where(Company.id.in_(ids)))
    by_id = {row.id: row.name for row in result.all()}
    companies = []
    for company_id in ids:
        name = by_id.get(company_id)
        if name is not None:
            companies.append({"id": company_id, "name": name})
    return companies


async def create_subscription_promotion(
    db: AsyncSession,
    admin: User,
    *,
    name: str,
    plan_code: str,
    period_months: int,
    promotional_amount: int,
    for_all_companies: bool = True,
    company_ids: list[UUID] | None = None,
    new_companies_only: bool = False,
    is_active: bool = True,
    max_uses: int | None = None,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
    description: str | None = None,
) -> SubscriptionPromotion:
    title = name.strip()
    if not title:
        raise AppError("Название акции не может быть пустым")

    await _validate_promotional_price(
        db,
        plan_code=plan_code,
        period_months=period_months,
        promotional_amount=promotional_amount,
    )

    if not for_all_companies:
        if not company_ids:
            raise AppError("Укажите company_ids — id компаний из GET /admin/companies")
        unique_ids = list(dict.fromkeys(company_ids))
        for company_id in unique_ids:
            from app.models.entities import Company

            company = await db.get(Company, company_id)
            if not company:
                raise NotFoundError(f"Компания с id {company_id} не найдена")
        company_ids = unique_ids
    elif company_ids:
        raise AppError("company_ids указываются только при for_all_companies=false")

    promotion = SubscriptionPromotion(
        name=title,
        plan_code=plan_code.strip(),
        period_months=period_months,
        promotional_amount=promotional_amount,
        for_all_companies=for_all_companies,
        company_ids=[str(item) for item in company_ids] if company_ids else None,
        new_companies_only=new_companies_only,
        is_active=is_active,
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
    plan_code: str | None = None,
    period_months: int | None = None,
    promotional_amount: int | None = None,
    for_all_companies: bool | None = None,
    company_ids: list[UUID] | None = None,
    new_companies_only: bool | None = None,
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

    next_plan_code = plan_code.strip() if plan_code is not None else promotion.plan_code
    next_period = period_months if period_months is not None else promotion.period_months
    next_amount = promotional_amount if promotional_amount is not None else promotion.promotional_amount

    if plan_code is not None or period_months is not None or promotional_amount is not None:
        await _validate_promotional_price(
            db,
            plan_code=next_plan_code,
            period_months=next_period,
            promotional_amount=next_amount,
        )
        promotion.plan_code = next_plan_code
        promotion.period_months = next_period
        promotion.promotional_amount = next_amount

    if for_all_companies is not None:
        promotion.for_all_companies = for_all_companies
        if for_all_companies:
            promotion.company_ids = None

    if clear_company_ids:
        promotion.company_ids = None
    elif company_ids is not None:
        unique_ids = list(dict.fromkeys(company_ids))
        for company_id in unique_ids:
            from app.models.entities import Company

            company = await db.get(Company, company_id)
            if not company:
                raise NotFoundError(f"Компания с id {company_id} не найдена")
        promotion.company_ids = [str(item) for item in unique_ids]
        promotion.for_all_companies = False

    if new_companies_only is not None:
        promotion.new_companies_only = new_companies_only

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
        raise ConflictError(
            "Укажите company_ids (id компаний) или установите for_all_companies=true"
        )

    await db.flush()
    return promotion
