from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError
from app.models.entities import Company, User
from app.services.subscription_service import (
    bind_subscription_to_company,
    get_subscription_by_id,
    list_unused_subscriptions,
)


async def require_unused_subscription(
    db: AsyncSession, user: User, subscription_id: UUID
):
    subscription = await get_subscription_by_id(db, subscription_id, user.id)
    if subscription.company_id is not None:
        raise ForbiddenError("Эта подписка уже привязана к компании")
    if subscription.status.value != "active":
        raise ForbiddenError("Подписка неактивна")
    return subscription


async def user_has_available_subscription_slot(db: AsyncSession, user_id: UUID) -> bool:
    return len(await list_unused_subscriptions(db, user_id)) > 0


async def create_company_with_subscription(
    db: AsyncSession, owner: User, name: str, subscription_id: UUID
) -> tuple[Company, ...]:
    subscription = await require_unused_subscription(db, owner, subscription_id)

    company = Company(name=name, owner_id=owner.id, is_owner_first_company=False)
    db.add(company)
    await db.flush()

    await bind_subscription_to_company(db, subscription, company)
    return company, subscription
