from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import MANAGE_MEMBERS
from app.core.tenant import TenantContext
from app.models.entities import CompanyMember, CompanyRole
from app.repositories.tenant_repository import TenantRepository


async def change_member_role(
    db: AsyncSession,
    tenant: TenantContext,
    member_id: UUID,
    role_id: UUID,
) -> CompanyMember:
    if not tenant.has_permission(MANAGE_MEMBERS):
        raise ForbiddenError("Нет права на смену роли сотрудника")

    repo = TenantRepository(db, tenant.company_id)
    member = await repo.get_member_by_id(member_id)
    if not member:
        raise NotFoundError("Сотрудник не найден")

    if member.user_id == tenant.company.owner_id:
        raise ForbiddenError("Нельзя менять роль владельца компании")

    role = await repo.get_role_by_id(role_id)
    if not role:
        raise NotFoundError("Роль не найдена в этой компании")

    member.role_id = role_id
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
    from app.core.permissions import MANAGE_ROLES
    from app.services.schedule_service import validate_permissions

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
