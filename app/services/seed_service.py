from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.entities import SubscriptionPlan, User

PLANS = [
    {
        "code": "starter",
        "name": "Стартовый",
        "description": "До 10 сотрудников, 3 филиала, 5 ролей",
        "max_users": 10,
        "max_branches": 3,
        "max_roles": 5,
        "price_monthly": 990,
        "sort_order": 1,
    },
    {
        "code": "business",
        "name": "Бизнес",
        "description": "До 50 сотрудников, 10 филиалов, 20 ролей",
        "max_users": 50,
        "max_branches": 10,
        "max_roles": 20,
        "price_monthly": 2990,
        "sort_order": 2,
    },
    {
        "code": "enterprise",
        "name": "Корпоративный",
        "description": "До 200 сотрудников, 50 филиалов, 100 ролей",
        "max_users": 200,
        "max_branches": 50,
        "max_roles": 100,
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
