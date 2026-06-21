from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.exceptions import AppError
from app.models.entities import User
from app.schemas.cabinet import InviteActivateRequest, InviteActivateResponse, InvitePreviewResponse
from app.schemas.schemas import PasswordChange, TokenResponse, UserRegister, UserResponse
from app.services.auth_service import authenticate_user, change_password, register_user
from app.services.invite_activation_service import activate_invite, get_invite_by_token, invite_preview_data

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    data: UserRegister,
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        return await register_user(db, data, request=request)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    result = await authenticate_user(
        db, form_data.username, form_data.password, request=request
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    _, token = result
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_user_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    try:
        await change_password(db, current_user, data)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/invites/{token}", response_model=InvitePreviewResponse)
async def preview_invite(token: str, db: AsyncSession = Depends(get_db)) -> InvitePreviewResponse:
    try:
        request = await get_invite_by_token(db, token)
        data = invite_preview_data(request)
        return InvitePreviewResponse(
            company_name=data["company_name"] or "",
            role_name=data["role_name"] or "",
            invite_email=data["invite_email"] or "",
            invite_full_name=data["invite_full_name"],
            invite_phone=data["invite_phone"],
            invited_by_name=data["invited_by_name"],
            message=data["message"],
            compensation_type=data["compensation_type"],
            compensation_rate=data["compensation_rate"],
            compensation_percent=data["compensation_percent"],
            token_expires_at=request.token_expires_at,
        )
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/invites/{token}/activate", response_model=InviteActivateResponse)
async def activate_employee_invite(
    token: str,
    data: InviteActivateRequest,
    db: AsyncSession = Depends(get_db),
) -> InviteActivateResponse:
    try:
        user, access_token, member = await activate_invite(
            db, token, password=data.password, full_name=data.full_name
        )
        await db.commit()
        return InviteActivateResponse(
            access_token=access_token,
            user_id=user.id,
            member_id=member.id,
            company_id=member.company_id,
        )
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
