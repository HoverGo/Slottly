from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppError
from app.schemas.public_booking import (
    PublicAppointmentCreate,
    PublicAppointmentResponse,
    PublicBookingCompanyResponse,
    PublicBookingMemberResponse,
    PublicBookingServiceResponse,
    PublicBookingSlotsResponse,
)
from app.schemas.reviews import (
    PublicReviewCreate,
    PublicReviewListResponse,
    PublicReviewResponse,
    CompanyRatingSummary,
    VisitMemberOptionResponse,
)
from app.services.review_service import (
    create_company_review,
    list_client_visit_members,
    list_public_reviews,
    review_to_public_dict,
)
from app.services.public_booking_service import (
    create_public_booking_appointment,
    get_company_by_booking_slug,
    get_public_booking_page,
    get_public_booking_slots,
    list_public_booking_members,
    list_public_booking_services,
)

router = APIRouter(prefix="/public/booking", tags=["public-booking"])


@router.get("/{slug}", response_model=PublicBookingCompanyResponse)
async def get_public_booking_company(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> PublicBookingCompanyResponse:
    try:
        data = await get_public_booking_page(db, slug)
        return PublicBookingCompanyResponse(**data)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/{slug}/reviews", response_model=PublicReviewListResponse)
async def list_public_company_reviews(
    slug: str,
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PublicReviewListResponse:
    try:
        company = await get_company_by_booking_slug(db, slug)
        rating, reviews = await list_public_reviews(db, company.id, limit=limit)
        return PublicReviewListResponse(
            rating=CompanyRatingSummary(**rating),
            reviews=[PublicReviewResponse(**review_to_public_dict(r)) for r in reviews],
        )
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/{slug}/reviews/visit-members", response_model=list[VisitMemberOptionResponse])
async def list_review_visit_members(
    slug: str,
    phone: str = Query(..., min_length=5, max_length=50),
    db: AsyncSession = Depends(get_db),
) -> list[VisitMemberOptionResponse]:
    try:
        company = await get_company_by_booking_slug(db, slug)
        members = await list_client_visit_members(db, company, phone=phone)
        return [VisitMemberOptionResponse(**member) for member in members]
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/{slug}/reviews", response_model=PublicReviewResponse, status_code=201)
async def create_public_review(
    slug: str,
    data: PublicReviewCreate,
    db: AsyncSession = Depends(get_db),
) -> PublicReviewResponse:
    try:
        company = await get_company_by_booking_slug(db, slug)
        review = await create_company_review(
            db,
            company,
            phone=data.client_phone,
            rating=data.rating,
            text=data.text,
            client_name=data.client_name,
            member_id=data.member_id,
        )
        return PublicReviewResponse(**review_to_public_dict(review))
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/{slug}/members", response_model=list[PublicBookingMemberResponse])
async def list_public_members(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> list[PublicBookingMemberResponse]:
    try:
        company = await get_company_by_booking_slug(db, slug)
        members = await list_public_booking_members(db, company)
        return [PublicBookingMemberResponse(**member) for member in members]
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/{slug}/services", response_model=list[PublicBookingServiceResponse])
async def list_public_services(
    slug: str,
    member_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[PublicBookingServiceResponse]:
    try:
        company = await get_company_by_booking_slug(db, slug)
        services = await list_public_booking_services(db, company, member_id=member_id)
        return [PublicBookingServiceResponse(**service) for service in services]
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/{slug}/members/{member_id}/slots", response_model=PublicBookingSlotsResponse)
async def get_public_member_slots(
    slug: str,
    member_id: UUID,
    service_id: UUID = Query(...),
    from_date: date = Query(...),
    to_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
) -> PublicBookingSlotsResponse:
    try:
        company = await get_company_by_booking_slug(db, slug)
        slots = await get_public_booking_slots(
            db,
            company,
            member_id,
            service_id=service_id,
            from_date=from_date,
            to_date=to_date,
        )
        return PublicBookingSlotsResponse(**slots)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post(
    "/{slug}/members/{member_id}/appointments",
    response_model=PublicAppointmentResponse,
    status_code=201,
)
async def create_public_appointment(
    slug: str,
    member_id: UUID,
    data: PublicAppointmentCreate,
    db: AsyncSession = Depends(get_db),
) -> PublicAppointmentResponse:
    try:
        company = await get_company_by_booking_slug(db, slug)
        appointment = await create_public_booking_appointment(
            db,
            company,
            member_id,
            service_id=data.service_id,
            starts_at=data.starts_at,
            client_name=data.client_name,
            client_full_name=data.client_full_name,
            client_phone=data.client_phone,
            client_email=str(data.client_email) if data.client_email else None,
            note=data.note,
        )
        return PublicAppointmentResponse(**appointment)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
