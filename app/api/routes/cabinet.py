from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.exceptions import AppError
from app.models.entities import User
from app.schemas.cabinet import (
    CabinetResponse,
    JoinRequestResponse,
    PlatformAnnouncementPublicResponse,
    UserSubscriptionResponse,
)
from app.schemas.schemas import CompanyResponse, UserResponse
from app.services.company_profile_service import company_to_response
from app.services.announcement_service import list_active_announcements
from app.services.company_service import get_active_subscription, list_accessible_companies
from app.services.join_request_service import (
    accept_join_request,
    join_request_response_data,
    list_user_pending_requests,
    reject_join_request,
)
from app.services.subscription_service import list_user_subscriptions
from app.services.user_subscription_service import user_has_available_subscription_slot

router = APIRouter(prefix="/cabinet", tags=["cabinet"])


def _join_request_response(req) -> JoinRequestResponse:
    return JoinRequestResponse(**join_request_response_data(req))


def _subscription_response(sub) -> UserSubscriptionResponse:
    return UserSubscriptionResponse(
        id=sub.id,
        plan_id=sub.plan_id,
        company_id=sub.company_id,
        status=sub.status.value,
        started_at=sub.started_at,
        expires_at=sub.expires_at,
        scheduled_plan_id=sub.scheduled_plan_id,
        scheduled_change_at=sub.scheduled_change_at,
        plan=sub.plan,
        scheduled_plan=sub.scheduled_plan,
        is_available_for_company=sub.company_id is None and sub.status.value == "active",
    )


def _company_response(company, has_sub: bool, is_owner: bool) -> CompanyResponse:
    return CompanyResponse(**company_to_response(company, has_sub=has_sub, is_owner=is_owner))


@router.get("", response_model=CabinetResponse)
async def get_cabinet(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CabinetResponse:
    subscriptions = await list_user_subscriptions(db, current_user.id)
    accessible = await list_accessible_companies(db, current_user.id)
    companies = []
    for company, is_owner in accessible:
        sub = await get_active_subscription(db, company.id)
        companies.append(_company_response(company, has_sub=sub is not None, is_owner=is_owner))

    pending = await list_user_pending_requests(db, current_user.id)
    available_slots = sum(1 for s in subscriptions if s.company_id is None and s.status.value == "active")
    announcements = await list_active_announcements(db)

    return CabinetResponse(
        user=UserResponse.model_validate(current_user),
        can_create_company=await user_has_available_subscription_slot(db, current_user.id),
        subscriptions=[_subscription_response(s) for s in subscriptions],
        available_subscription_slots=available_slots,
        companies=companies,
        pending_join_requests=[_join_request_response(r) for r in pending],
        platform_announcements=[
            PlatformAnnouncementPublicResponse(
                id=item.id,
                title=item.title,
                message=item.message,
                maintenance_starts_at=item.maintenance_starts_at,
                maintenance_ends_at=item.maintenance_ends_at,
                created_at=item.created_at,
            )
            for item in announcements
        ],
    )


@router.get("/join-requests", response_model=list[JoinRequestResponse])
async def list_my_join_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[JoinRequestResponse]:
    pending = await list_user_pending_requests(db, current_user.id)
    return [_join_request_response(r) for r in pending]


@router.post("/join-requests/{request_id}/accept", status_code=201)
async def accept_request(
    request_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        member = await accept_join_request(db, current_user, request_id)
        return {"member_id": str(member.id), "company_id": str(member.company_id)}
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/join-requests/{request_id}/reject", response_model=JoinRequestResponse)
async def reject_request(
    request_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JoinRequestResponse:
    try:
        request = await reject_join_request(db, current_user, request_id)
        await db.refresh(request, ["company", "role", "invited_by"])
        return JoinRequestResponse(**join_request_response_data(request))
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
