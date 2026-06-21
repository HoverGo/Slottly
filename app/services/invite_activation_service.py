from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.security import create_access_token, hash_password
from app.models.entities import CompanyJoinRequest, CompanyMember, JoinRequestStatus, User
from app.services.compensation_service import copy_compensation_to_member
from app.services.company_service import check_subscription_limit
from app.services.join_request_service import join_request_response_data
from app.services.subscription_limits_service import grant_basic_subscription


async def get_invite_by_token(db: AsyncSession, token: str) -> CompanyJoinRequest:
    result = await db.execute(
        select(CompanyJoinRequest)
        .options(
            selectinload(CompanyJoinRequest.company),
            selectinload(CompanyJoinRequest.role),
            selectinload(CompanyJoinRequest.invited_by),
        )
        .where(
            CompanyJoinRequest.activation_token == token,
            CompanyJoinRequest.status == JoinRequestStatus.PENDING_ACTIVATION,
        )
    )
    request = result.scalar_one_or_none()
    if not request:
        raise NotFoundError("Приглашение не найдено или уже использовано")
    if request.token_expires_at and request.token_expires_at <= datetime.now(UTC):
        raise AppError("Срок действия приглашения истёк")
    return request


async def activate_invite(
    db: AsyncSession,
    token: str,
    *,
    password: str,
    full_name: str | None = None,
) -> tuple[User, str, CompanyMember]:
    request = await get_invite_by_token(db, token)
    email = (request.invite_email or "").lower()
    if not email:
        raise AppError("Некорректное приглашение")

    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise ConflictError("Пользователь с таким email уже зарегистрирован")

    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name or request.invite_full_name or email,
    )
    db.add(user)
    await db.flush()
    await grant_basic_subscription(db, user.id)
    await check_subscription_limit(db, request.company, add_users=1)

    member = CompanyMember(
        company_id=request.company_id,
        user_id=user.id,
        role_id=request.role_id,
    )
    copy_compensation_to_member(member, request)
    db.add(member)

    request.user_id = user.id
    request.status = JoinRequestStatus.ACCEPTED
    request.responded_at = datetime.now(UTC)
    request.activation_token = None
    request.token_expires_at = None

    await db.flush()
    access_token = create_access_token(str(user.id))
    return user, access_token, member


def invite_preview_data(request: CompanyJoinRequest) -> dict:
    data = join_request_response_data(request)
    data.pop("activation_url", None)
    return data
