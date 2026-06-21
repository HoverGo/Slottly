from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.core.tenant import TenantContext
from app.models.entities import (
    Branch,
    Company,
    CompanyRole,
    SubscriptionPlan,
    User,
)
from app.repositories.tenant_repository import TenantRepository
from app.services.subscription_service import (
    get_company_subscription,
    get_company_usage,
    list_available_plans_for_company,
)
from app.services.user_subscription_service import create_company_with_subscription


def _repo(db: AsyncSession, company_id: UUID) -> TenantRepository:
    return TenantRepository(db, company_id)


async def get_active_subscription(db: AsyncSession, company_id: UUID):
    return await get_company_subscription(db, company_id)


async def count_company_entities(db: AsyncSession, company_id: UUID) -> tuple[int, int, int]:
    return await get_company_usage(db, company_id)


async def require_active_subscription(db: AsyncSession, company: Company):
    subscription = await get_company_subscription(db, company.id)
    if not subscription:
        raise ForbiddenError(
            "Подписка компании истекла или отсутствует. "
            "Продлите или оформите подписку: POST /api/v1/payments/checkout"
        )
    return subscription


from app.services.subscription_limits_service import (
    count_company_appointments_in_month,
    count_company_services,
)


async def check_subscription_limit(
    db: AsyncSession,
    company: Company,
    *,
    add_users: int = 0,
    add_branches: int = 0,
    add_roles: int = 0,
    add_services: int = 0,
    add_appointments: int = 0,
) -> None:
    from app.services.company_offer_service import get_effective_limits

    subscription = await require_active_subscription(db, company)
    limits = await get_effective_limits(db, company.id, subscription.plan)
    users, branches, roles = await count_company_entities(db, company.id)
    services = await count_company_services(db, company.id)
    appointments = await count_company_appointments_in_month(db, company.id)

    if users + add_users > limits["max_users"]:
        raise ForbiddenError(f"Лимит пользователей ({limits['max_users']}) исчерпан")
    if branches + add_branches > limits["max_branches"]:
        raise ForbiddenError(f"Лимит филиалов ({limits['max_branches']}) исчерпан")
    if roles + add_roles > limits["max_roles"]:
        raise ForbiddenError(f"Лимит ролей ({limits['max_roles']}) исчерпан")
    if services + add_services > limits["max_services"]:
        raise ForbiddenError(f"Лимит услуг ({limits['max_services']}) исчерпан")
    if appointments + add_appointments > limits["max_appointments_per_month"]:
        raise ForbiddenError(
            f"Лимит записей в месяц ({limits['max_appointments_per_month']}) исчерпан"
        )


async def get_subscription_limits(db: AsyncSession, company: Company) -> dict:
    from app.services.company_offer_service import (
        get_active_company_subscription_offer,
        get_effective_limits,
    )

    subscription = await get_company_subscription(db, company.id)
    users, branches, roles = await count_company_entities(db, company.id)
    services = await count_company_services(db, company.id)
    appointments = await count_company_appointments_in_month(db, company.id)
    offer = await get_active_company_subscription_offer(db, company.id)

    if subscription:
        plan = subscription.plan
        limits = await get_effective_limits(db, company.id, plan)
        result = {
            **limits,
            "current_users": users,
            "current_branches": branches,
            "current_roles": roles,
            "current_services": services,
            "current_appointments_this_month": appointments,
            "has_active_subscription": True,
            "expires_at": subscription.expires_at,
            "scheduled_plan_code": subscription.scheduled_plan.code if subscription.scheduled_plan else None,
            "scheduled_change_at": subscription.scheduled_change_at,
            "plan_price_monthly": plan.price_monthly,
            "price_monthly": offer.price_monthly if offer else plan.price_monthly,
            "has_custom_offer": offer is not None,
            "custom_offer_name": (offer.display_name or offer.name) if offer else None,
        }
        return result

    return {
        "max_users": 0,
        "max_branches": 0,
        "max_roles": 0,
        "max_services": 0,
        "max_appointments_per_month": 0,
        "current_users": users,
        "current_branches": branches,
        "current_roles": roles,
        "current_services": services,
        "current_appointments_this_month": appointments,
        "has_active_subscription": False,
        "expires_at": None,
        "scheduled_plan_code": None,
        "scheduled_change_at": None,
        "plan_price_monthly": None,
        "price_monthly": None,
        "has_custom_offer": offer is not None,
        "custom_offer_name": (offer.display_name or offer.name) if offer else None,
    }


async def list_accessible_companies(db: AsyncSession, user_id: UUID) -> list[tuple[Company, bool]]:
    from app.models.entities import CompanyMember

    owned = await db.execute(select(Company).where(Company.owner_id == user_id))
    owned_companies = {c.id: (c, True) for c in owned.scalars().all()}

    member_result = await db.execute(
        select(Company)
        .join(CompanyMember, CompanyMember.company_id == Company.id)
        .where(CompanyMember.user_id == user_id)
    )
    for company in member_result.scalars().all():
        if company.id not in owned_companies:
            owned_companies[company.id] = (company, False)

    return list(owned_companies.values())


async def create_company(db: AsyncSession, owner: User, name: str, subscription_id: UUID) -> Company:
    company, _ = await create_company_with_subscription(db, owner, name, subscription_id)
    return company


async def get_plan_by_code(db: AsyncSession, code: str) -> SubscriptionPlan:
    result = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.code == code))
    plan = result.scalar_one_or_none()
    if not plan:
        raise NotFoundError(f"Тариф '{code}' не найден")
    return plan


async def list_all_plans(db: AsyncSession) -> list[SubscriptionPlan]:
    result = await db.execute(select(SubscriptionPlan).order_by(SubscriptionPlan.sort_order))
    return list(result.scalars().all())


async def create_role(
    db: AsyncSession, tenant: TenantContext, name: str, description: str | None, permissions: list[str]
) -> CompanyRole:
    from app.core.permissions import MANAGE_ROLES
    from app.services.schedule_service import validate_permissions

    if not tenant.has_permission(MANAGE_ROLES):
        raise ForbiddenError("Нет права на управление ролями")

    repo = _repo(db, tenant.company_id)
    await check_subscription_limit(db, tenant.company, add_roles=1)

    if await repo.get_role_by_name(name):
        raise ConflictError(f"Роль '{name}' уже существует в этой компании")

    role = CompanyRole(
        company_id=tenant.company_id,
        name=name,
        description=description,
        permissions=validate_permissions(permissions),
    )
    db.add(role)
    await db.flush()
    return role


async def create_branch(
    db: AsyncSession, tenant: TenantContext, name: str, address: str | None
) -> Branch:
    await check_subscription_limit(db, tenant.company, add_branches=1)

    branch = Branch(company_id=tenant.company_id, name=name, address=address)
    db.add(branch)
    await db.flush()
    return branch


async def get_company_available_plans(db: AsyncSession, company_id: UUID) -> list[SubscriptionPlan]:
    return await list_available_plans_for_company(db, company_id)
