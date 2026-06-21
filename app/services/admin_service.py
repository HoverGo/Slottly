from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entities import (
    Company,
    Payment,
    PaymentStatus,
    PromoCode,
    SubscriptionPromotion,
    SubscriptionStatus,
    User,
    UserSubscription,
)
from app.services.subscription_service import sync_subscription_state
from app.services.support_service import count_open_tickets


async def get_dashboard_stats(db: AsyncSession) -> dict[str, int]:
    users = await db.scalar(select(func.count()).select_from(User)) or 0
    companies = await db.scalar(select(func.count()).select_from(Company)) or 0
    payments = (
        await db.scalar(
            select(func.count()).select_from(Payment).where(Payment.status == PaymentStatus.SUCCEEDED)
        )
        or 0
    )
    subscriptions = (
        await db.scalar(select(func.count()).select_from(UserSubscription)) or 0
    )
    promo_codes = await db.scalar(select(func.count()).select_from(PromoCode)) or 0
    active_promo_codes = (
        await db.scalar(
            select(func.count()).select_from(PromoCode).where(PromoCode.is_active.is_(True))
        )
        or 0
    )
    subscription_promotions = (
        await db.scalar(select(func.count()).select_from(SubscriptionPromotion)) or 0
    )
    active_subscription_promotions = (
        await db.scalar(
            select(func.count())
            .select_from(SubscriptionPromotion)
            .where(SubscriptionPromotion.is_active.is_(True))
        )
        or 0
    )

    open_support = await count_open_tickets(db)

    return {
        "users_count": users,
        "companies_count": companies,
        "successful_payments_count": payments,
        "subscriptions_count": subscriptions,
        "promo_codes_count": promo_codes,
        "active_promo_codes_count": active_promo_codes,
        "subscription_promotions_count": subscription_promotions,
        "active_subscription_promotions_count": active_subscription_promotions,
        "open_support_tickets_count": open_support,
    }


async def list_users_admin(
    db: AsyncSession, *, limit: int = 50, offset: int = 0
) -> list[User]:
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all())


async def list_companies_admin(
    db: AsyncSession, *, limit: int = 50, offset: int = 0
) -> list[Company]:
    result = await db.execute(
        select(Company)
        .options(
            selectinload(Company.owner),
            selectinload(Company.subscription).selectinload(UserSubscription.plan),
            selectinload(Company.subscription).selectinload(UserSubscription.payment),
        )
        .order_by(Company.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


def _subscription_is_active(subscription: UserSubscription | None) -> bool:
    if not subscription or subscription.status != SubscriptionStatus.ACTIVE:
        return False
    if subscription.expires_at and subscription.expires_at <= datetime.now(UTC):
        return False
    return True


def _subscription_is_paid(subscription: UserSubscription | None) -> bool:
    if not subscription or not subscription.payment:
        return False
    return subscription.payment.status == PaymentStatus.SUCCEEDED


async def build_admin_company_response(db: AsyncSession, company: Company) -> dict:
    subscription = company.subscription
    if subscription:
        await sync_subscription_state(db, subscription)

    payment = subscription.payment if subscription else None
    plan = subscription.plan if subscription else None

    return {
        "id": company.id,
        "name": company.name,
        "owner_id": company.owner_id,
        "owner_email": company.owner.email if company.owner else None,
        "owner_name": company.owner.full_name if company.owner else None,
        "is_owner_first_company": company.is_owner_first_company,
        "created_at": company.created_at,
        "subscription_id": subscription.id if subscription else None,
        "plan_code": plan.code if plan else None,
        "plan_name": plan.name if plan else None,
        "subscription_status": subscription.status.value if subscription else None,
        "expires_at": subscription.expires_at if subscription else None,
        "is_subscription_active": _subscription_is_active(subscription),
        "is_paid": _subscription_is_paid(subscription),
        "is_free_plan": plan.price_monthly == 0 if plan else False,
        "last_payment_status": payment.status.value if payment else None,
        "last_payment_paid_at": payment.paid_at if payment else None,
        "last_payment_amount": payment.amount if payment else None,
    }


async def set_user_platform_admin(
    db: AsyncSession, user_id: UUID, is_platform_admin: bool
) -> User:
    user = await db.get(User, user_id)
    if not user:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("Пользователь не найден")
    user.is_platform_admin = is_platform_admin
    await db.flush()
    return user


async def set_user_platform_support(
    db: AsyncSession, user_id: UUID, is_platform_support: bool
) -> User:
    user = await db.get(User, user_id)
    if not user:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("Пользователь не найден")
    user.is_platform_support = is_platform_support
    await db.flush()
    return user
