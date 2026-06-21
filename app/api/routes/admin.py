from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_platform_admin
from app.core.database import get_db
from app.core.exceptions import AppError
from app.models.entities import User
from app.schemas.admin import (
    AdminCompanyResponse,
    AdminDashboardResponse,
    AdminUserResponse,
    PlatformAdminUpdate,
    PlatformAnnouncementCreate,
    PlatformAnnouncementResponse,
    PlatformAnnouncementUpdate,
    PlatformSupportUpdate,
    PromoCodeCreate,
    PromoCodeResponse,
    PromoCodeUpdate,
)
from app.services.admin_service import (
    build_admin_company_response,
    get_dashboard_stats,
    list_companies_admin,
    list_users_admin,
    set_user_platform_admin,
    set_user_platform_support,
)
from app.services.announcement_service import (
    create_announcement,
    list_announcements_admin,
    update_announcement,
)
from app.services.promo_service import create_promo_code, list_promo_codes, update_promo_code

router = APIRouter(prefix="/admin", tags=["admin"])


def _promo_to_response(promo) -> PromoCodeResponse:
    return PromoCodeResponse(
        id=promo.id,
        code=promo.code,
        discount_percent=promo.discount_percent,
        user_id=promo.user_id,
        user_email=promo.user.email if promo.user else None,
        user_name=promo.user.full_name if promo.user else None,
        plan_codes=promo.plan_codes,
        actions=promo.actions,
        max_uses=promo.max_uses,
        used_count=promo.used_count,
        valid_from=promo.valid_from,
        valid_until=promo.valid_until,
        is_active=promo.is_active,
        description=promo.description,
        created_by_id=promo.created_by_id,
        created_at=promo.created_at,
    )


@router.get("/dashboard", response_model=AdminDashboardResponse)
async def admin_dashboard(
    _: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminDashboardResponse:
    stats = await get_dashboard_stats(db)
    return AdminDashboardResponse(**stats)


@router.get("/users", response_model=list[AdminUserResponse])
async def admin_list_users(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> list[AdminUserResponse]:
    users = await list_users_admin(db, limit=limit, offset=offset)
    return [AdminUserResponse.model_validate(user) for user in users]


@router.patch("/users/{user_id}/platform-admin", response_model=AdminUserResponse)
async def admin_set_platform_admin(
    user_id: UUID,
    data: PlatformAdminUpdate,
    current_admin: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminUserResponse:
    if user_id == current_admin.id and not data.is_platform_admin:
        raise HTTPException(status_code=400, detail="Нельзя снять права у самого себя")
    try:
        user = await set_user_platform_admin(db, user_id, data.is_platform_admin)
        return AdminUserResponse.model_validate(user)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.patch("/users/{user_id}/platform-support", response_model=AdminUserResponse)
async def admin_set_platform_support(
    user_id: UUID,
    data: PlatformSupportUpdate,
    _: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminUserResponse:
    try:
        user = await set_user_platform_support(db, user_id, data.is_platform_support)
        return AdminUserResponse.model_validate(user)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/companies", response_model=list[AdminCompanyResponse])
async def admin_list_companies(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> list[AdminCompanyResponse]:
    companies = await list_companies_admin(db, limit=limit, offset=offset)
    result = []
    for company in companies:
        data = await build_admin_company_response(db, company)
        result.append(AdminCompanyResponse(**data))
    return result


def _announcement_response(item) -> PlatformAnnouncementResponse:
    return PlatformAnnouncementResponse(
        id=item.id,
        title=item.title,
        message=item.message,
        maintenance_starts_at=item.maintenance_starts_at,
        maintenance_ends_at=item.maintenance_ends_at,
        is_active=item.is_active,
        created_by_id=item.created_by_id,
        created_by_name=item.created_by.full_name if item.created_by else None,
        created_at=item.created_at,
    )


@router.get("/announcements", response_model=list[PlatformAnnouncementResponse])
async def admin_list_announcements(
    _: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> list[PlatformAnnouncementResponse]:
    items = await list_announcements_admin(db)
    return [_announcement_response(item) for item in items]


@router.post("/announcements", response_model=PlatformAnnouncementResponse, status_code=201)
async def admin_create_announcement(
    data: PlatformAnnouncementCreate,
    admin: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> PlatformAnnouncementResponse:
    try:
        item = await create_announcement(
            db,
            admin,
            title=data.title,
            message=data.message,
            maintenance_starts_at=data.maintenance_starts_at,
            maintenance_ends_at=data.maintenance_ends_at,
        )
        await db.refresh(item, ["created_by"])
        return _announcement_response(item)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.patch("/announcements/{announcement_id}", response_model=PlatformAnnouncementResponse)
async def admin_update_announcement(
    announcement_id: UUID,
    data: PlatformAnnouncementUpdate,
    _: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> PlatformAnnouncementResponse:
    try:
        item = await update_announcement(
            db,
            announcement_id,
            title=data.title,
            message=data.message,
            maintenance_starts_at=data.maintenance_starts_at,
            maintenance_ends_at=data.maintenance_ends_at,
            is_active=data.is_active,
            clear_maintenance_starts_at=data.clear_maintenance_starts_at,
            clear_maintenance_ends_at=data.clear_maintenance_ends_at,
        )
        await db.refresh(item, ["created_by"])
        return _announcement_response(item)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/promo-codes", response_model=list[PromoCodeResponse])
async def admin_list_promo_codes(
    _: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> list[PromoCodeResponse]:
    promos = await list_promo_codes(db)
    return [_promo_to_response(promo) for promo in promos]


@router.post("/promo-codes", response_model=PromoCodeResponse, status_code=201)
async def admin_create_promo_code(
    data: PromoCodeCreate,
    admin: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> PromoCodeResponse:
    try:
        user_id = data.user_id
        if data.user_email and not user_id:
            result = await db.execute(select(User).where(User.email == data.user_email))
            target = result.scalar_one_or_none()
            if not target:
                raise AppError("Пользователь с указанным email не найден")
            user_id = target.id

        promo = await create_promo_code(
            db,
            admin,
            code=data.code,
            discount_percent=data.discount_percent,
            user_id=user_id,
            plan_codes=data.plan_codes,
            actions=[action.value for action in data.actions] if data.actions else None,
            max_uses=data.max_uses,
            valid_from=data.valid_from,
            valid_until=data.valid_until,
            description=data.description,
        )
        await db.refresh(promo, ["user"])
        return _promo_to_response(promo)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.patch("/promo-codes/{promo_id}", response_model=PromoCodeResponse)
async def admin_update_promo_code(
    promo_id: UUID,
    data: PromoCodeUpdate,
    _: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> PromoCodeResponse:
    try:
        promo = await update_promo_code(
            db,
            promo_id,
            discount_percent=data.discount_percent,
            plan_codes=data.plan_codes,
            actions=[action.value for action in data.actions] if data.actions is not None else None,
            max_uses=data.max_uses,
            valid_from=data.valid_from,
            valid_until=data.valid_until,
            is_active=data.is_active,
            description=data.description,
            clear_valid_from=data.clear_valid_from,
            clear_valid_until=data.clear_valid_until,
        )
        await db.refresh(promo, ["user"])
        return _promo_to_response(promo)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
