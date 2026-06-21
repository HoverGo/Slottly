from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, NotFoundError
from app.models.entities import Company, CompanySubscriptionOffer, SubscriptionPlan, User
from app.services.company_service import count_company_entities, get_plan_by_code
from app.services.subscription_limits_service import (
    count_company_appointments_in_month,
    count_company_services,
)
from app.services.subscription_service import calculate_price


def _offer_is_active_now(offer: CompanySubscriptionOffer) -> bool:
    if not offer.is_active:
        return False
    now = datetime.now(UTC)
    if offer.valid_from and now < offer.valid_from:
        return False
    if offer.valid_until and now > offer.valid_until:
        return False
    return True


async def get_company_subscription_offer(
    db: AsyncSession, company_id: UUID
) -> CompanySubscriptionOffer | None:
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(CompanySubscriptionOffer)
        .options(selectinload(CompanySubscriptionOffer.company))
        .where(CompanySubscriptionOffer.company_id == company_id)
    )
    return result.scalar_one_or_none()


async def get_active_company_subscription_offer(
    db: AsyncSession, company_id: UUID
) -> CompanySubscriptionOffer | None:
    offer = await get_company_subscription_offer(db, company_id)
    if offer and _offer_is_active_now(offer):
        return offer
    return None


def effective_limits_from_offer(offer: CompanySubscriptionOffer) -> dict[str, int]:
    return {
        "max_users": offer.max_users,
        "max_branches": offer.max_branches,
        "max_roles": offer.max_roles,
        "max_services": offer.max_services,
        "max_appointments_per_month": offer.max_appointments_per_month,
    }


def effective_limits_from_plan(plan: SubscriptionPlan) -> dict[str, int]:
    return {
        "max_users": plan.max_users,
        "max_branches": plan.max_branches,
        "max_roles": plan.max_roles,
        "max_services": plan.max_services,
        "max_appointments_per_month": plan.max_appointments_per_month,
    }


async def get_effective_limits(
    db: AsyncSession, company_id: UUID, plan: SubscriptionPlan
) -> dict[str, int]:
    offer = await get_active_company_subscription_offer(db, company_id)
    if offer:
        return effective_limits_from_offer(offer)
    return effective_limits_from_plan(plan)


async def resolve_company_checkout_amount(
    db: AsyncSession,
    *,
    company_id: UUID | None,
    plan: SubscriptionPlan,
    period_months: int,
) -> tuple[int, CompanySubscriptionOffer | None]:
    default_amount = calculate_price(plan, period_months)
    if company_id is None:
        return default_amount, None
    offer = await get_active_company_subscription_offer(db, company_id)
    if not offer:
        return default_amount, None
    return offer.price_monthly * period_months, offer


async def _validate_offer_limits_against_usage(
    db: AsyncSession,
    company_id: UUID,
    *,
    max_users: int,
    max_branches: int,
    max_roles: int,
    max_services: int,
    max_appointments_per_month: int,
) -> None:
    users, branches, roles = await count_company_entities(db, company_id)
    services = await count_company_services(db, company_id)
    appointments = await count_company_appointments_in_month(db, company_id)

    if max_users < users:
        raise AppError(f"max_users не может быть меньше текущего числа сотрудников ({users})")
    if max_branches < branches:
        raise AppError(f"max_branches не может быть меньше текущего числа филиалов ({branches})")
    if max_roles < roles:
        raise AppError(f"max_roles не может быть меньше текущего числа ролей ({roles})")
    if max_services < services:
        raise AppError(f"max_services не может быть меньше текущего числа услуг ({services})")
    if max_appointments_per_month < appointments:
        raise AppError(
            "max_appointments_per_month не может быть меньше записей в текущем месяце "
            f"({appointments})"
        )


async def _validate_offer_price(
    db: AsyncSession,
    company_id: UUID,
    base_plan_code: str | None,
    price_monthly: int,
) -> None:
    if price_monthly < 0:
        raise AppError("price_monthly не может быть отрицательным")

    plan: SubscriptionPlan | None = None
    if base_plan_code:
        plan = await get_plan_by_code(db, base_plan_code)
    else:
        from app.services.subscription_service import get_company_subscription

        subscription = await get_company_subscription(db, company_id)
        if subscription:
            plan = subscription.plan

    if plan and price_monthly >= plan.price_monthly:
        raise AppError(
            f"Индивидуальная цена ({price_monthly} ₽) должна быть ниже базовой "
            f"({plan.price_monthly} ₽/мес.)"
        )


def offer_to_dict(offer: CompanySubscriptionOffer) -> dict:
    return {
        "id": offer.id,
        "company_id": offer.company_id,
        "name": offer.name,
        "display_name": offer.display_name,
        "price_monthly": offer.price_monthly,
        "max_users": offer.max_users,
        "max_branches": offer.max_branches,
        "max_roles": offer.max_roles,
        "max_services": offer.max_services,
        "max_appointments_per_month": offer.max_appointments_per_month,
        "base_plan_code": offer.base_plan_code,
        "valid_from": offer.valid_from,
        "valid_until": offer.valid_until,
        "is_active": offer.is_active,
        "description": offer.description,
        "created_by_id": offer.created_by_id,
        "created_at": offer.created_at,
        "updated_at": offer.updated_at,
    }


async def upsert_company_subscription_offer(
    db: AsyncSession,
    admin: User,
    company_id: UUID,
    *,
    name: str,
    price_monthly: int,
    max_users: int,
    max_branches: int,
    max_roles: int,
    max_services: int,
    max_appointments_per_month: int,
    display_name: str | None = None,
    base_plan_code: str | None = None,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
    is_active: bool = True,
    description: str | None = None,
) -> CompanySubscriptionOffer:
    company = await db.get(Company, company_id)
    if not company:
        raise NotFoundError("Компания не найдена")

    title = name.strip()
    if not title:
        raise AppError("Название предложения не может быть пустым")

    if base_plan_code:
        await get_plan_by_code(db, base_plan_code)

    await _validate_offer_price(db, company_id, base_plan_code, price_monthly)
    await _validate_offer_limits_against_usage(
        db,
        company_id,
        max_users=max_users,
        max_branches=max_branches,
        max_roles=max_roles,
        max_services=max_services,
        max_appointments_per_month=max_appointments_per_month,
    )

    offer = await get_company_subscription_offer(db, company_id)
    if offer is None:
        offer = CompanySubscriptionOffer(
            company_id=company_id,
            created_by_id=admin.id,
        )
        db.add(offer)

    offer.name = title
    offer.display_name = display_name.strip() if display_name else None
    offer.price_monthly = price_monthly
    offer.max_users = max_users
    offer.max_branches = max_branches
    offer.max_roles = max_roles
    offer.max_services = max_services
    offer.max_appointments_per_month = max_appointments_per_month
    offer.base_plan_code = base_plan_code.strip() if base_plan_code else None
    offer.valid_from = valid_from
    offer.valid_until = valid_until
    offer.is_active = is_active
    offer.description = description
    offer.created_by_id = admin.id

    await db.flush()
    return offer


async def update_company_subscription_offer(
    db: AsyncSession,
    company_id: UUID,
    *,
    name: str | None = None,
    price_monthly: int | None = None,
    max_users: int | None = None,
    max_branches: int | None = None,
    max_roles: int | None = None,
    max_services: int | None = None,
    max_appointments_per_month: int | None = None,
    display_name: str | None = None,
    clear_display_name: bool = False,
    base_plan_code: str | None = None,
    clear_base_plan_code: bool = False,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
    clear_valid_from: bool = False,
    clear_valid_until: bool = False,
    is_active: bool | None = None,
    description: str | None = None,
) -> CompanySubscriptionOffer:
    offer = await get_company_subscription_offer(db, company_id)
    if not offer:
        raise NotFoundError("Индивидуальное предложение для компании не найдено")

    if name is not None:
        title = name.strip()
        if not title:
            raise AppError("Название предложения не может быть пустым")
        offer.name = title

    if clear_display_name:
        offer.display_name = None
    elif display_name is not None:
        offer.display_name = display_name.strip() or None

    next_price = price_monthly if price_monthly is not None else offer.price_monthly
    next_base = offer.base_plan_code
    if clear_base_plan_code:
        next_base = None
    elif base_plan_code is not None:
        next_base = base_plan_code.strip() or None
        if next_base:
            await get_plan_by_code(db, next_base)

    if price_monthly is not None or base_plan_code is not None or clear_base_plan_code:
        await _validate_offer_price(db, company_id, next_base, next_price)
        offer.price_monthly = next_price
        offer.base_plan_code = next_base

    next_limits = {
        "max_users": max_users if max_users is not None else offer.max_users,
        "max_branches": max_branches if max_branches is not None else offer.max_branches,
        "max_roles": max_roles if max_roles is not None else offer.max_roles,
        "max_services": max_services if max_services is not None else offer.max_services,
        "max_appointments_per_month": (
            max_appointments_per_month
            if max_appointments_per_month is not None
            else offer.max_appointments_per_month
        ),
    }
    if any(
        value is not None
        for value in (
            max_users,
            max_branches,
            max_roles,
            max_services,
            max_appointments_per_month,
        )
    ):
        await _validate_offer_limits_against_usage(db, company_id, **next_limits)
        offer.max_users = next_limits["max_users"]
        offer.max_branches = next_limits["max_branches"]
        offer.max_roles = next_limits["max_roles"]
        offer.max_services = next_limits["max_services"]
        offer.max_appointments_per_month = next_limits["max_appointments_per_month"]

    if clear_valid_from:
        offer.valid_from = None
    elif valid_from is not None:
        offer.valid_from = valid_from

    if clear_valid_until:
        offer.valid_until = None
    elif valid_until is not None:
        offer.valid_until = valid_until

    if is_active is not None:
        offer.is_active = is_active

    if description is not None:
        offer.description = description

    await db.flush()
    return offer


async def list_company_subscription_offers(db: AsyncSession) -> list[CompanySubscriptionOffer]:
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(CompanySubscriptionOffer)
        .options(selectinload(CompanySubscriptionOffer.company))
        .order_by(CompanySubscriptionOffer.updated_at.desc())
    )
    return list(result.scalars().all())
