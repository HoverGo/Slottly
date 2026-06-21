from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppError, NotFoundError
from app.models.entities import (
    AppointmentStatus,
    Company,
    CompanyMember,
    CompanyReview,
    MemberAppointment,
)
from app.repositories.tenant_repository import TenantRepository
from app.services.client_service import get_client_by_phone
from app.services.media_service import public_media_url


async def get_rating_summary(db: AsyncSession, company_id: UUID) -> dict:
    result = await db.execute(
        select(func.avg(CompanyReview.rating), func.count())
        .select_from(CompanyReview)
        .where(
            CompanyReview.company_id == company_id,
            CompanyReview.is_visible.is_(True),
        )
    )
    average, count = result.one()
    review_count = count or 0
    return {
        "average": round(float(average), 2) if average is not None else 0.0,
        "count": review_count,
    }


def review_to_public_dict(review: CompanyReview) -> dict:
    member_user = review.member.user if review.member else None
    return {
        "id": review.id,
        "rating": review.rating,
        "text": review.text,
        "client_name": review.client_display_name,
        "member_id": review.member_id,
        "member_name": member_user.full_name if member_user else None,
        "created_at": review.created_at,
    }


def review_to_dict(review: CompanyReview) -> dict:
    member_user = review.member.user if review.member else None
    return {
        "id": review.id,
        "company_id": review.company_id,
        "client_id": review.client_id,
        "client_name": review.client_display_name,
        "member_id": review.member_id,
        "member_name": member_user.full_name if member_user else None,
        "rating": review.rating,
        "text": review.text,
        "is_visible": review.is_visible,
        "created_at": review.created_at,
    }


async def _client_has_visits(db: AsyncSession, company_id: UUID, client_id: UUID) -> bool:
    result = await db.scalar(
        select(func.count())
        .select_from(MemberAppointment)
        .where(
            MemberAppointment.company_id == company_id,
            MemberAppointment.client_id == client_id,
            MemberAppointment.status != AppointmentStatus.CANCELLED,
        )
    )
    return (result or 0) > 0


async def _client_visited_member(
    db: AsyncSession, company_id: UUID, client_id: UUID, member_id: UUID
) -> bool:
    result = await db.scalar(
        select(func.count())
        .select_from(MemberAppointment)
        .where(
            MemberAppointment.company_id == company_id,
            MemberAppointment.client_id == client_id,
            MemberAppointment.member_id == member_id,
            MemberAppointment.status != AppointmentStatus.CANCELLED,
        )
    )
    return (result or 0) > 0


async def list_client_visit_members(
    db: AsyncSession,
    company: Company,
    *,
    phone: str,
) -> list[dict]:
    client = await get_client_by_phone(db, company.id, phone)
    result = await db.execute(
        select(MemberAppointment.member_id)
        .where(
            MemberAppointment.company_id == company.id,
            MemberAppointment.client_id == client.id,
            MemberAppointment.status != AppointmentStatus.CANCELLED,
        )
        .distinct()
    )
    member_ids = [row[0] for row in result.all()]
    if not member_ids:
        return []

    members_result = await db.execute(
        select(CompanyMember)
        .options(selectinload(CompanyMember.user))
        .where(
            CompanyMember.company_id == company.id,
            CompanyMember.id.in_(member_ids),
        )
        .order_by(CompanyMember.created_at)
    )
    return [
        {
            "id": member.id,
            "full_name": member.user.full_name if member.user else "Специалист",
            "photo_url": public_media_url(member.photo_path),
        }
        for member in members_result.scalars().all()
    ]


async def create_company_review(
    db: AsyncSession,
    company: Company,
    *,
    phone: str,
    rating: int,
    text: str,
    client_name: str | None = None,
    member_id: UUID | None = None,
) -> CompanyReview:
    try:
        client = await get_client_by_phone(db, company.id, phone)
    except NotFoundError as exc:
        raise AppError("Оставить отзыв могут только клиенты, которые записывались в компанию") from exc

    if not await _client_has_visits(db, company.id, client.id):
        raise AppError("Нет записей для этого номера телефона")

    if member_id is not None:
        repo = TenantRepository(db, company.id)
        member = await repo.get_member_by_id(member_id)
        if not member:
            raise NotFoundError("Специалист не найден")
        if not await _client_visited_member(db, company.id, client.id, member_id):
            raise AppError("Клиент не записывался к выбранному специалисту")

    display_name = client_name.strip() if client_name and client_name.strip() else client.name or client.full_name

    review = CompanyReview(
        company_id=company.id,
        client_id=client.id,
        member_id=member_id,
        client_display_name=display_name,
        rating=rating,
        text=text.strip(),
        is_visible=True,
    )
    db.add(review)
    await db.flush()
    await db.refresh(review, ["member"])
    if review.member:
        await db.refresh(review.member, ["user"])
    return review


async def list_public_reviews(
    db: AsyncSession,
    company_id: UUID,
    *,
    limit: int = 50,
) -> tuple[dict, list[CompanyReview]]:
    rating = await get_rating_summary(db, company_id)
    result = await db.execute(
        select(CompanyReview)
        .options(selectinload(CompanyReview.member).selectinload(CompanyMember.user))
        .where(
            CompanyReview.company_id == company_id,
            CompanyReview.is_visible.is_(True),
        )
        .order_by(CompanyReview.created_at.desc())
        .limit(min(limit, 100))
    )
    return rating, list(result.scalars().all())


async def list_company_reviews(
    db: AsyncSession,
    company_id: UUID,
    *,
    limit: int = 100,
) -> tuple[dict, list[CompanyReview]]:
    rating = await get_rating_summary(db, company_id)
    result = await db.execute(
        select(CompanyReview)
        .options(selectinload(CompanyReview.member).selectinload(CompanyMember.user))
        .where(CompanyReview.company_id == company_id)
        .order_by(CompanyReview.created_at.desc())
        .limit(min(limit, 500))
    )
    return rating, list(result.scalars().all())
