from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import Request

from app.core.brute_force import login_brute_force
from app.core.exceptions import AppError, ConflictError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.entities import User
from app.schemas.schemas import PasswordChange, UserRegister
from app.services.audit_service import record_audit_event

from app.services.subscription_limits_service import grant_basic_subscription


async def register_user(
    db: AsyncSession,
    data: UserRegister,
    *,
    request: Request | None = None,
) -> User:
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise ConflictError("Пользователь с таким email уже существует")

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
    )
    db.add(user)
    await db.flush()
    await grant_basic_subscription(db, user.id)
    if request is not None:
        await record_audit_event(
            db,
            action="register.success",
            category="auth",
            actor_user_id=user.id,
            actor_email=user.email,
            success=True,
            request=request,
        )
    return user


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
    *,
    request: Request | None = None,
) -> tuple[User, str] | None:
    if request is not None:
        await login_brute_force.assert_can_attempt(email, request)

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not user.is_active or not verify_password(password, user.hashed_password):
        if request is not None:
            await login_brute_force.register_failure(email, request)
            await record_audit_event(
                db,
                action="login.failure",
                category="auth",
                actor_email=email.strip().lower(),
                success=False,
                request=request,
                details={"reason": "invalid_credentials"},
            )
        return None

    if request is not None:
        await login_brute_force.register_success(email, request)
        await record_audit_event(
            db,
            action="login.success",
            category="auth",
            actor_user_id=user.id,
            actor_email=user.email,
            success=True,
            request=request,
        )
    token = create_access_token(str(user.id))
    return user, token


async def change_password(db: AsyncSession, user: User, data: PasswordChange) -> None:
    if not verify_password(data.current_password, user.hashed_password):
        raise AppError("Неверный текущий пароль", status_code=400)

    user.hashed_password = hash_password(data.new_password)
    await db.flush()
