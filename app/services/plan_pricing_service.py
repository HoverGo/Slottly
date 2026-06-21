from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import SubscriptionPlan, SubscriptionPromotion, User
from app.models.enums import PaymentAction
from app.schemas.schemas import (
    SubscriptionPlanPeriodPromotion,
    SubscriptionPlanPromotionInfo,
    SubscriptionPlanResponse,
)
from app.services.promo_service import calculate_discount
from app.services.promotion_service import (
    list_eligible_promotions_for_plan_display,
    promotion_base_amount,
    promotion_checkout_amounts,
    promotion_discounted_monthly_price,
    resolve_best_promotion_for_checkout,
)
from app.services.subscription_service import get_subscription_by_id


async def resolve_checkout_company_id(
    db: AsyncSession,
    user: User,
    action: PaymentAction,
    subscription_id: UUID | None,
) -> UUID | None:
    if not subscription_id:
        return None
    subscription = await get_subscription_by_id(db, subscription_id, user.id)
    return subscription.company_id


def _promotion_info(
    plan: SubscriptionPlan, promotion: SubscriptionPromotion
) -> SubscriptionPlanPromotionInfo:
    original_amount = promotion_base_amount(plan, promotion)
    return SubscriptionPlanPromotionInfo(
        id=promotion.id,
        name=promotion.name,
        period_months=promotion.period_months,
        original_amount=original_amount,
        promotional_amount=promotion.promotional_amount,
        new_companies_only=promotion.new_companies_only,
    )


def build_plan_response(
    plan: SubscriptionPlan,
    promotions: list[SubscriptionPromotion] | None = None,
) -> SubscriptionPlanResponse:
    data = SubscriptionPlanResponse.model_validate(plan)
    if not promotions:
        return data

    period_items = [_promotion_info(plan, promotion) for promotion in promotions]
    one_month = next((item for item in promotions if item.period_months == 1), None)
    promotional_price_monthly = (
        promotion_discounted_monthly_price(plan, one_month) if one_month else None
    )
    active_promotion = _promotion_info(plan, one_month) if one_month else None

    return data.model_copy(
        update={
            "promotional_price_monthly": promotional_price_monthly,
            "active_promotion": active_promotion,
            "period_promotions": period_items,
        }
    )


async def build_plan_responses_with_promotions(
    db: AsyncSession,
    plans: list[SubscriptionPlan],
    *,
    company_id: UUID | None = None,
) -> list[SubscriptionPlanResponse]:
    result: list[SubscriptionPlanResponse] = []
    for plan in plans:
        promotions = await list_eligible_promotions_for_plan_display(
            db, plan=plan, company_id=company_id
        )
        result.append(build_plan_response(plan, promotions))
    return result


def apply_checkout_discounts(
    original_amount: int,
    *,
    promotion: SubscriptionPromotion | None,
    plan: SubscriptionPlan | None,
    promo_discount_percent: int | None,
) -> tuple[int, int, SubscriptionPromotion | None, bool]:
    """Возвращает итог, скидку, применённую акцию и флаг что сработал промокод"""
    promotion_amount = original_amount
    promotion_discount = 0
    if promotion and plan:
        promotion_amount, promotion_discount = promotion_checkout_amounts(plan, promotion)

    if promo_discount_percent is None:
        return promotion_amount, promotion_discount, promotion, False

    promo_amount, promo_discount = calculate_discount(original_amount, promo_discount_percent)
    if promo_amount <= promotion_amount:
        return promo_amount, promo_discount, None, True
    return promotion_amount, promotion_discount, promotion, False
