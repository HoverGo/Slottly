from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import SubscriptionPlan, SubscriptionPromotion, User
from app.models.enums import PaymentAction
from app.schemas.schemas import SubscriptionPlanPromotionInfo, SubscriptionPlanResponse
from app.services.promo_service import calculate_discount
from app.services.promotion_service import (
    promotion_discounted_monthly_price,
    resolve_best_promotion_for_checkout,
    resolve_best_promotion_for_plan_display,
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


def build_plan_response(
    plan: SubscriptionPlan,
    promotion: SubscriptionPromotion | None = None,
) -> SubscriptionPlanResponse:
    data = SubscriptionPlanResponse.model_validate(plan)
    if not promotion:
        return data
    promotional_price = promotion_discounted_monthly_price(plan, promotion)
    return data.model_copy(
        update={
            "promotional_price_monthly": promotional_price,
            "active_promotion": SubscriptionPlanPromotionInfo(
                id=promotion.id,
                name=promotion.name,
                discount_percent=promotion.discount_percent,
                first_plan_purchase_only=promotion.first_plan_purchase_only,
            ),
        }
    )


async def build_plan_responses_with_promotions(
    db: AsyncSession,
    plans: list[SubscriptionPlan],
    *,
    company_id: UUID | None = None,
    action: PaymentAction = PaymentAction.PURCHASE,
) -> list[SubscriptionPlanResponse]:
    result: list[SubscriptionPlanResponse] = []
    for plan in plans:
        if company_id is not None:
            promotion = await resolve_best_promotion_for_checkout(
                db, plan=plan, action=action, company_id=company_id
            )
        else:
            promotion = await resolve_best_promotion_for_plan_display(db, plan=plan)
        result.append(build_plan_response(plan, promotion))
    return result


def apply_checkout_discounts(
    original_amount: int,
    *,
    promotion: SubscriptionPromotion | None,
    promo_discount_percent: int | None,
) -> tuple[int, int, SubscriptionPromotion | None, bool]:
    """Возвращает итог, скидку, применённую акцию и флаг что сработал промокод"""
    promotion_amount = original_amount
    promotion_discount = 0
    if promotion:
        promotion_amount, promotion_discount = calculate_discount(
            original_amount, promotion.discount_percent
        )

    if promo_discount_percent is None:
        return promotion_amount, promotion_discount, promotion, False

    promo_amount, promo_discount = calculate_discount(original_amount, promo_discount_percent)
    if promo_discount >= promotion_discount:
        return promo_amount, promo_discount, None, True
    return promotion_amount, promotion_discount, promotion, False
