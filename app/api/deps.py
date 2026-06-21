from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import decode_access_token
from app.core.permissions import VIEW_STATISTICS
from app.core.platform_roles import user_can_manage_company_offers, user_is_platform_staff
from app.core.tenant import TenantContext, set_tenant_context
from app.models.entities import Company, CompanyMember, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный токен")

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден")
    return user


async def _resolve_company_access(
    company_id: UUID,
    current_user: User,
    db: AsyncSession,
) -> TenantContext | None:
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        return None

    if company.owner_id == current_user.id:
        return TenantContext(
            company_id=company.id,
            company=company,
            user_id=current_user.id,
            is_owner=True,
        )

    member_result = await db.execute(
        select(CompanyMember)
        .options(selectinload(CompanyMember.role))
        .where(
            CompanyMember.company_id == company_id,
            CompanyMember.user_id == current_user.id,
        )
    )
    member = member_result.scalar_one_or_none()
    if member:
        perms = frozenset(member.role.permissions or [])
        return TenantContext(
            company_id=company.id,
            company=company,
            user_id=current_user.id,
            is_owner=False,
            member=member,
            permissions=perms,
        )

    return None


async def get_company_tenant(
    company_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TenantContext:
    ctx = await _resolve_company_access(company_id, current_user, db)
    if ctx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Компания не найдена")
    set_tenant_context(ctx)
    return ctx


def require_permission(permission: str):
    async def _checker(tenant: TenantContext = Depends(get_company_tenant)) -> TenantContext:
        if not tenant.has_permission(permission):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Компания не найдена")
        return tenant

    return _checker


def require_statistics_access():
    async def _checker(tenant: TenantContext = Depends(get_company_tenant)) -> TenantContext:
        if tenant.is_owner or tenant.has_permission(VIEW_STATISTICS):
            return tenant
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Компания не найдена")

    return _checker


async def require_platform_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для администратора платформы",
        )
    return current_user


async def require_platform_staff(
    current_user: User = Depends(get_current_user),
) -> User:
    if not user_is_platform_staff(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для техподдержки или администратора платформы",
        )
    return current_user


async def require_platform_offer_manager(
    current_user: User = Depends(get_current_user),
) -> User:
    if not user_can_manage_company_offers(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для главного администратора или администратора платформы",
        )
    return current_user


async def get_company_tenant_owner(
    tenant: TenantContext = Depends(get_company_tenant),
) -> TenantContext:
    if not tenant.is_owner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Компания не найдена")
    return tenant
