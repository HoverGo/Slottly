from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entities import Company, Payment, PaymentStatus, PromoCode, User, UserSubscription
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

    open_support = await count_open_tickets(db)

    return {
        "users_count": users,
        "companies_count": companies,
        "successful_payments_count": payments,
        "subscriptions_count": subscriptions,
        "promo_codes_count": promo_codes,
        "active_promo_codes_count": active_promo_codes,
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
        .options(selectinload(Company.owner))
        .order_by(Company.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


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
