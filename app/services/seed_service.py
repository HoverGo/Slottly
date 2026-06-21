from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.entities import SubscriptionPlan, User

PLANS = [
    {
        "code": "basic",
        "name": "Базовый",
        "description": "Бесплатно: 3 сотрудника, 5 услуг, 50 записей в месяц",
        "max_users": 3,
        "max_branches": 1,
        "max_roles": 3,
        "max_services": 5,
        "max_appointments_per_month": 50,
        "price_monthly": 0,
        "sort_order": 0,
    },
    {
        "code": "starter",
        "name": "Стартовый",
        "description": "До 10 сотрудников, 3 филиала, 5 ролей, 500 записей/мес",
        "max_users": 10,
        "max_branches": 3,
        "max_roles": 5,
        "max_services": 20,
        "max_appointments_per_month": 500,
        "price_monthly": 990,
        "sort_order": 1,
    },
    {
        "code": "business",
        "name": "Бизнес",
        "description": "До 50 сотрудников, 10 филиалов, 20 ролей, 3000 записей/мес",
        "max_users": 50,
        "max_branches": 10,
        "max_roles": 20,
        "max_services": 100,
        "max_appointments_per_month": 3000,
        "price_monthly": 2990,
        "sort_order": 2,
    },
    {
        "code": "enterprise",
        "name": "Корпоративный",
        "description": "До 200 сотрудников, 50 филиалов, 100 ролей, 20000 записей/мес",
        "max_users": 200,
        "max_branches": 50,
        "max_roles": 100,
        "max_services": 500,
        "max_appointments_per_month": 20000,
        "price_monthly": 9990,
        "sort_order": 3,
    },
]


async def seed_subscription_plans(db: AsyncSession) -> None:
    result = await db.execute(select(SubscriptionPlan).limit(1))
    if result.scalar_one_or_none():
        return

    for plan_data in PLANS:
        db.add(SubscriptionPlan(**plan_data))
    await db.flush()


async def promote_platform_admins(db: AsyncSession) -> None:
    emails = settings.platform_admin_emails_list
    if not emails:
        return

    result = await db.execute(select(User).where(User.email.in_(emails)))
    for user in result.scalars().all():
        if not user.is_platform_admin:
            user.is_platform_admin = True
    await db.flush()


async def promote_platform_support(db: AsyncSession) -> None:
    emails = settings.platform_support_emails_list
    if not emails:
        return

    result = await db.execute(select(User).where(User.email.in_(emails)))
    for user in result.scalars().all():
        if not user.is_platform_support:
            user.is_platform_support = True
    await db.flush()


async def ensure_basic_subscriptions_for_users(db: AsyncSession) -> None:
    from app.models.entities import UserSubscription
    from app.services.subscription_limits_service import get_plan_by_code, grant_basic_subscription

    plan = await get_plan_by_code(db, "basic")
    if not plan:
        return

    users = await db.execute(select(User.id))
    for (user_id,) in users.all():
        has_any = await db.scalar(
            select(UserSubscription.id).where(UserSubscription.user_id == user_id).limit(1)
        )
        if not has_any:
            await grant_basic_subscription(db, user_id)
    await db.flush()
