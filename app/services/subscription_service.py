from datetime import UTC, datetime, timedelta
from uuid import UUID

from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppError, ForbiddenError, NotFoundError
from app.models.entities import (
    Company,
    SubscriptionPlan,
    SubscriptionStatus,
    User,
    UserSubscription,
)
from app.models.enums import VALID_BILLING_MONTHS
from app.repositories.tenant_repository import TenantRepository


def calculate_price(plan: SubscriptionPlan, period_months: int) -> int:
    return plan.price_monthly * period_months


def plan_fits_usage(plan: SubscriptionPlan, users: int, branches: int, roles: int) -> bool:
    return users <= plan.max_users and branches <= plan.max_branches and roles <= plan.max_roles


def is_upgrade(current: SubscriptionPlan, new: SubscriptionPlan) -> bool:
    return (
        new.max_users >= current.max_users
        and new.max_branches >= current.max_branches
        and new.max_roles >= current.max_roles
        and (
            new.max_users > current.max_users
            or new.max_branches > current.max_branches
            or new.max_roles > current.max_roles
        )
    )


def is_downgrade(current: SubscriptionPlan, new: SubscriptionPlan) -> bool:
    return (
        new.max_users <= current.max_users
        and new.max_branches <= current.max_branches
        and new.max_roles <= current.max_roles
        and (
            new.max_users < current.max_users
            or new.max_branches < current.max_branches
            or new.max_roles < current.max_roles
        )
    )


async def sync_subscription_state(db: AsyncSession, subscription: UserSubscription) -> UserSubscription:
    now = datetime.now(UTC)

    if subscription.status == SubscriptionStatus.ACTIVE and subscription.expires_at and subscription.expires_at <= now:
        subscription.status = SubscriptionStatus.EXPIRED

    if (
        subscription.status == SubscriptionStatus.ACTIVE
        and subscription.scheduled_plan_id
        and subscription.scheduled_change_at
        and subscription.scheduled_change_at <= now
    ):
        subscription.plan_id = subscription.scheduled_plan_id
        subscription.scheduled_plan_id = None
        subscription.scheduled_change_at = None

    await db.flush()
    return subscription


async def get_subscription_by_id(
    db: AsyncSession, subscription_id: UUID, user_id: UUID
) -> UserSubscription:
    result = await db.execute(
        select(UserSubscription)
        .options(
            selectinload(UserSubscription.plan),
            selectinload(UserSubscription.scheduled_plan),
        )
        .where(UserSubscription.id == subscription_id, UserSubscription.user_id == user_id)
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        raise NotFoundError("Подписка не найдена")
    return await sync_subscription_state(db, subscription)


async def get_company_subscription(db: AsyncSession, company_id: UUID) -> UserSubscription | None:
    result = await db.execute(
        select(UserSubscription)
        .options(
            selectinload(UserSubscription.plan),
            selectinload(UserSubscription.scheduled_plan),
        )
        .where(
            UserSubscription.company_id == company_id,
            UserSubscription.status == SubscriptionStatus.ACTIVE,
        )
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        return None
    subscription = await sync_subscription_state(db, subscription)
    if subscription.status != SubscriptionStatus.ACTIVE:
        return None
    if subscription.expires_at and subscription.expires_at <= datetime.now(UTC):
        return None
    return subscription


async def list_user_subscriptions(db: AsyncSession, user_id: UUID) -> list[UserSubscription]:
    result = await db.execute(
        select(UserSubscription)
        .options(
            selectinload(UserSubscription.plan),
            selectinload(UserSubscription.scheduled_plan),
            selectinload(UserSubscription.company),
        )
        .where(UserSubscription.user_id == user_id)
        .order_by(UserSubscription.started_at.desc())
    )
    subs = list(result.scalars().all())
    for sub in subs:
        await sync_subscription_state(db, sub)
    return subs


async def list_unused_subscriptions(db: AsyncSession, user_id: UUID) -> list[UserSubscription]:
    now = datetime.now(UTC)
    result = await db.execute(
        select(UserSubscription)
        .options(selectinload(UserSubscription.plan))
        .where(
            UserSubscription.user_id == user_id,
            UserSubscription.company_id.is_(None),
            UserSubscription.status == SubscriptionStatus.ACTIVE,
            (UserSubscription.expires_at.is_(None)) | (UserSubscription.expires_at > now),
        )
    )
    return list(result.scalars().all())


async def get_company_usage(db: AsyncSession, company_id: UUID) -> tuple[int, int, int]:
    return await TenantRepository(db, company_id).count_entities()


async def validate_plan_for_company(
    db: AsyncSession, company_id: UUID, plan: SubscriptionPlan
) -> None:
    from app.services.company_offer_service import get_active_company_subscription_offer

    offer = await get_active_company_subscription_offer(db, company_id)
    if offer:
        return

    users, branches, roles = await get_company_usage(db, company_id)
    if not plan_fits_usage(plan, users, branches, roles):
        raise ForbiddenError(
            f"Тариф «{plan.name}» не подходит: в компании {users} сотр., "
            f"{branches} филиалов, {roles} ролей. "
            f"Лимиты тарифа: {plan.max_users}/{plan.max_branches}/{plan.max_roles}"
        )


async def list_available_plans_for_company(
    db: AsyncSession, company_id: UUID
) -> list[SubscriptionPlan]:
    users, branches, roles = await get_company_usage(db, company_id)
    result = await db.execute(select(SubscriptionPlan).order_by(SubscriptionPlan.sort_order))
    return [p for p in result.scalars().all() if plan_fits_usage(p, users, branches, roles)]


async def create_subscription_from_payment(
    db: AsyncSession,
    user: User,
    plan: SubscriptionPlan,
    period_months: int,
    payment_id: UUID,
) -> UserSubscription:
    if period_months not in VALID_BILLING_MONTHS:
        raise AppError("Период оплаты: 1, 3, 6 или 12 месяцев")

    now = datetime.now(UTC)
    subscription = UserSubscription(
        user_id=user.id,
        plan_id=plan.id,
        payment_id=payment_id,
        started_at=now,
        expires_at=now + relativedelta(months=period_months),
    )
    db.add(subscription)
    await db.flush()
    return subscription


async def renew_subscription(
    db: AsyncSession, subscription: UserSubscription, period_months: int, payment_id: UUID
) -> UserSubscription:
    if period_months not in VALID_BILLING_MONTHS:
        raise AppError("Период оплаты: 1, 3, 6 или 12 месяцев")

    now = datetime.now(UTC)
    base = subscription.expires_at if subscription.expires_at and subscription.expires_at > now else now
    subscription.expires_at = base + relativedelta(months=period_months)
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.payment_id = payment_id
    await db.flush()
    return subscription


async def change_plan(
    db: AsyncSession,
    subscription: UserSubscription,
    new_plan: SubscriptionPlan,
    payment_id: UUID | None = None,
) -> UserSubscription:
    if not subscription.company_id:
        subscription.plan_id = new_plan.id
        if payment_id:
            subscription.payment_id = payment_id
        subscription.scheduled_plan_id = None
        subscription.scheduled_change_at = None
        await db.flush()
        return subscription

    await validate_plan_for_company(db, subscription.company_id, new_plan)
    current = subscription.plan

    if is_upgrade(current, new_plan):
        subscription.plan_id = new_plan.id
        subscription.scheduled_plan_id = None
        subscription.scheduled_change_at = None
        if payment_id:
            subscription.payment_id = payment_id
    elif is_downgrade(current, new_plan):
        if not subscription.expires_at:
            raise AppError("Невозможно запланировать даунгрейд без даты окончания периода")
        subscription.scheduled_plan_id = new_plan.id
        subscription.scheduled_change_at = subscription.expires_at
        if payment_id:
            subscription.payment_id = payment_id
    else:
        raise AppError("Выберите тариф с другим уровнем лимитов")

    await db.flush()
    return subscription


async def bind_subscription_to_company(
    db: AsyncSession, subscription: UserSubscription, company: Company
) -> UserSubscription:
    if subscription.company_id:
        raise AppError("Подписка уже привязана к компании")
    if subscription.status != SubscriptionStatus.ACTIVE:
        raise ForbiddenError("Подписка неактивна")
    if subscription.expires_at and subscription.expires_at <= datetime.now(UTC):
        raise ForbiddenError("Срок подписки истёк. Продлите её перед созданием компании")

    subscription.company_id = company.id
    await db.flush()
    return subscription
