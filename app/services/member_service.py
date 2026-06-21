from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import MANAGE_MEMBERS, MANAGE_ROLES
from app.core.tenant import TenantContext
from app.models.entities import CompanyMember, CompanyRole, CompensationType
from app.repositories.tenant_repository import TenantRepository
from app.services.compensation_service import validate_compensation
from app.services.schedule_service import validate_permissions


async def update_member(
    db: AsyncSession,
    tenant: TenantContext,
    member_id: UUID,
    *,
    role_id: UUID | None = None,
    compensation_type: CompensationType | None = None,
    compensation_rate: int | None = None,
    compensation_percent: int | None = None,
    clear_compensation: bool = False,
) -> CompanyMember:
    if not tenant.has_permission(MANAGE_MEMBERS):
        raise ForbiddenError("Нет права на управление сотрудниками")

    repo = TenantRepository(db, tenant.company_id)
    member = await repo.get_member_by_id(member_id)
    if not member:
        raise NotFoundError("Сотрудник не найден")

    if member.user_id == tenant.company.owner_id and role_id is not None:
        raise ForbiddenError("Нельзя менять роль владельца компании")

    if role_id is not None:
        role = await repo.get_role_by_id(role_id)
        if not role:
            raise NotFoundError("Роль не найдена в этой компании")
        member.role_id = role_id

    if clear_compensation:
        member.compensation_type = None
        member.compensation_rate = None
        member.compensation_percent = None
    elif compensation_type is not None or compensation_rate is not None or compensation_percent is not None:
        new_type = compensation_type if compensation_type is not None else member.compensation_type
        new_rate = compensation_rate if compensation_rate is not None else member.compensation_rate
        new_percent = (
            compensation_percent if compensation_percent is not None else member.compensation_percent
        )
        validate_compensation(new_type, new_rate, new_percent)
        member.compensation_type = new_type
        member.compensation_rate = new_rate
        member.compensation_percent = new_percent

    await db.flush()
    await db.refresh(member, ["role"])
    return member


async def update_role(
    db: AsyncSession,
    tenant: TenantContext,
    role_id: UUID,
    *,
    name: str | None = None,
    description: str | None = None,
    permissions: list[str] | None = None,
) -> CompanyRole:
    if not tenant.has_permission(MANAGE_ROLES):
        raise ForbiddenError("Нет права на управление ролями")

    repo = TenantRepository(db, tenant.company_id)
    role = await repo.get_role_by_id(role_id)
    if not role:
        raise NotFoundError("Роль не найдена")

    if name and name != role.name:
        if await repo.get_role_by_name(name):
            raise ConflictError(f"Роль '{name}' уже существует")
        role.name = name

    if description is not None:
        role.description = description

    if permissions is not None:
        role.permissions = validate_permissions(permissions)

    await db.flush()
    return role

