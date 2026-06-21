from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.tenant import TenantContext
from app.models.entities import (
    CompanyJoinRequest,
    CompanyMember,
    CompensationType,
    JoinRequestStatus,
    User,
)
from app.repositories.tenant_repository import TenantRepository
from app.services.compensation_service import copy_compensation_to_member, validate_compensation
from app.services.company_service import check_subscription_limit
from app.services.subscription_limits_service import (
    build_activation_url,
    generate_invite_token,
    invite_token_expires_at,
)


def join_request_response_data(request: CompanyJoinRequest) -> dict:
    activation_url = None
    if request.status == JoinRequestStatus.PENDING_ACTIVATION and request.activation_token:
        activation_url = build_activation_url(request.activation_token)

    return {
        "id": request.id,
        "company_id": request.company_id,
        "user_id": request.user_id,
        "role_id": request.role_id,
        "invited_by_id": request.invited_by_id,
        "status": request.status,
        "message": request.message,
        "created_at": request.created_at,
        "responded_at": request.responded_at,
        "company_name": request.company.name if request.company else None,
        "role_name": request.role.name if request.role else None,
        "invited_by_name": request.invited_by.full_name if request.invited_by else None,
        "invite_email": request.invite_email,
        "invite_full_name": request.invite_full_name,
        "invite_phone": request.invite_phone,
        "activation_url": activation_url,
        "compensation_type": request.compensation_type.value if request.compensation_type else None,
        "compensation_rate": request.compensation_rate,
        "compensation_percent": request.compensation_percent,
    }


async def create_join_request(
    db: AsyncSession,
    tenant: TenantContext,
    invited_by: User,
    user_email: str,
    role_id: UUID,
    message: str | None = None,
    *,
    full_name: str | None = None,
    phone: str | None = None,
    compensation_type: CompensationType | None = None,
    compensation_rate: int | None = None,
    compensation_percent: int | None = None,
) -> CompanyJoinRequest:
    validate_compensation(compensation_type, compensation_rate, compensation_percent)
    await check_subscription_limit(db, tenant.company, add_users=1)

    repo = TenantRepository(db, tenant.company_id)
    role = await repo.get_role_by_id(role_id)
    if not role:
        raise NotFoundError("Роль не найдена в этой компании")

    email = user_email.strip().lower()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
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
            invite_email=email,
            role_id=role_id,
            invited_by_id=invited_by.id,
            message=message,
            compensation_type=compensation_type,
            compensation_rate=compensation_rate,
            compensation_percent=compensation_percent,
            status=JoinRequestStatus.PENDING,
        )
    else:
        if not full_name or not full_name.strip():
            raise AppError("Для нового сотрудника укажите full_name")

        pending_invite = await db.execute(
            select(CompanyJoinRequest).where(
                CompanyJoinRequest.company_id == tenant.company_id,
                CompanyJoinRequest.invite_email == email,
                CompanyJoinRequest.status == JoinRequestStatus.PENDING_ACTIVATION,
            )
        )
        if pending_invite.scalar_one_or_none():
            raise ConflictError("Приглашение на этот email уже отправлено")

        token = generate_invite_token()
        request = CompanyJoinRequest(
            company_id=tenant.company_id,
            user_id=None,
            invite_email=email,
            invite_full_name=full_name.strip(),
            invite_phone=phone,
            activation_token=token,
            token_expires_at=invite_token_expires_at(),
            role_id=role_id,
            invited_by_id=invited_by.id,
            message=message,
            compensation_type=compensation_type,
            compensation_rate=compensation_rate,
            compensation_percent=compensation_percent,
            status=JoinRequestStatus.PENDING_ACTIVATION,
        )

    db.add(request)
    await db.flush()
    await db.refresh(request, ["company", "role", "invited_by"])
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
            selectinload(CompanyJoinRequest.company),
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
    copy_compensation_to_member(member, request)
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

