from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.tenant import TenantContext
from app.models.entities import (
    CompanyJoinRequest,
    CompanyMember,
    JoinRequestStatus,
    User,
)
from app.services.company_service import check_subscription_limit
from app.repositories.tenant_repository import TenantRepository


async def create_join_request(
    db: AsyncSession,
    tenant: TenantContext,
    invited_by: User,
    user_email: str,
    role_id: UUID,
    message: str | None = None,
) -> CompanyJoinRequest:
    await check_subscription_limit(db, tenant.company, add_users=1)

    repo = TenantRepository(db, tenant.company_id)
    role = await repo.get_role_by_id(role_id)
    if not role:
        raise NotFoundError("Роль не найдена в этой компании")

    result = await db.execute(select(User).where(User.email == user_email))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("Пользователь с таким email не зарегистрирован")

    if user.id == tenant.company.owner_id:
        raise ConflictError("Владелец уже состоит в компании")

    if await repo.get_member_by_user_id(user.id):
        raise ConflictError("Пользователь уже состоит в компании")

    pending = await db.execute(
        select(CompanyJoinRequest).where(
            CompanyJoinRequest.company_id == tenant.company_id,
            CompanyJoinRequest.user_id == user.id,
            CompanyJoinRequest.status == JoinRequestStatus.PENDING,
        )
    )
    if pending.scalar_one_or_none():
        raise ConflictError("Запрос на присоединение уже отправлен")

    request = CompanyJoinRequest(
        company_id=tenant.company_id,
        user_id=user.id,
        role_id=role_id,
        invited_by_id=invited_by.id,
        message=message,
    )
    db.add(request)
    await db.flush()
    await db.refresh(request, ["company", "role"])
    return request


async def list_company_join_requests(
    db: AsyncSession, company_id: UUID
) -> list[CompanyJoinRequest]:
    result = await db.execute(
        select(CompanyJoinRequest)
        .options(
            selectinload(CompanyJoinRequest.user),
            selectinload(CompanyJoinRequest.role),
            selectinload(CompanyJoinRequest.invited_by),
        )
        .where(CompanyJoinRequest.company_id == company_id)
        .order_by(CompanyJoinRequest.created_at.desc())
    )
    return list(result.scalars().all())


async def list_user_pending_requests(db: AsyncSession, user_id: UUID) -> list[CompanyJoinRequest]:
    result = await db.execute(
        select(CompanyJoinRequest)
        .options(
            selectinload(CompanyJoinRequest.company),
            selectinload(CompanyJoinRequest.role),
            selectinload(CompanyJoinRequest.invited_by),
        )
        .where(
            CompanyJoinRequest.user_id == user_id,
            CompanyJoinRequest.status == JoinRequestStatus.PENDING,
        )
        .order_by(CompanyJoinRequest.created_at.desc())
    )
    return list(result.scalars().all())


async def accept_join_request(db: AsyncSession, user: User, request_id: UUID) -> CompanyMember:
    result = await db.execute(
        select(CompanyJoinRequest)
        .options(selectinload(CompanyJoinRequest.company))
        .where(
            CompanyJoinRequest.id == request_id,
            CompanyJoinRequest.user_id == user.id,
        )
    )
    request = result.scalar_one_or_none()
    if not request:
        raise NotFoundError("Запрос не найден")
    if request.status != JoinRequestStatus.PENDING:
        raise ConflictError("Запрос уже обработан")

    repo = TenantRepository(db, request.company_id)
    if await repo.get_member_by_user_id(user.id):
        request.status = JoinRequestStatus.CANCELLED
        request.responded_at = datetime.now(UTC)
        raise ConflictError("Вы уже состоите в этой компании")

    await check_subscription_limit(db, request.company, add_users=1)

    member = CompanyMember(
        company_id=request.company_id,
        user_id=user.id,
        role_id=request.role_id,
    )
    db.add(member)
    request.status = JoinRequestStatus.ACCEPTED
    request.responded_at = datetime.now(UTC)
    await db.flush()
    return member


async def reject_join_request(db: AsyncSession, user: User, request_id: UUID) -> CompanyJoinRequest:
    result = await db.execute(
        select(CompanyJoinRequest).where(
            CompanyJoinRequest.id == request_id,
            CompanyJoinRequest.user_id == user.id,
        )
    )
    request = result.scalar_one_or_none()
    if not request:
        raise NotFoundError("Запрос не найден")
    if request.status != JoinRequestStatus.PENDING:
        raise ConflictError("Запрос уже обработан")

    request.status = JoinRequestStatus.REJECTED
    request.responded_at = datetime.now(UTC)
    await db.flush()
    return request
