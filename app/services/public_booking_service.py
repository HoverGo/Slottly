from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppError, ForbiddenError, NotFoundError
from app.models.entities import AppointmentStatus, Company, CompanyMember, MemberWorkSchedule
from app.repositories.tenant_repository import TenantRepository
from app.schemas.schemas import CompanyWorkingHours
from app.services.appointment_service import create_appointment_for_company, public_appointment_to_response
from app.services.company_service import get_active_subscription
from app.services.media_service import public_media_url
from app.services.schedule_service import generate_slots_for_day, list_schedule_exceptions
from app.services.service_catalog_service import get_company_service, service_to_response


def _working_hours_from_dict(data: dict | None) -> CompanyWorkingHours | None:
    if not data:
        return None
    return CompanyWorkingHours.model_validate(data)


def _gallery_photo_to_dict(photo) -> dict:
    return {
        "id": photo.id,
        "url": public_media_url(photo.path),
        "sort_order": photo.sort_order,
        "created_at": photo.created_at,
    }


async def get_company_by_booking_slug(db: AsyncSession, slug: str) -> Company:
    normalized = slug.strip().lower()
    result = await db.execute(select(Company).where(Company.booking_slug == normalized))
    company = result.scalar_one_or_none()
    if not company or not company.public_booking_enabled:
        raise NotFoundError("Онлайн-запись недоступна")
    subscription = await get_active_subscription(db, company.id)
    if not subscription:
        raise ForbiddenError("Онлайн-запись временно недоступна")
    return company


async def get_public_booking_page(db: AsyncSession, slug: str) -> dict:
    from app.services.review_service import get_rating_summary

    company = await get_company_by_booking_slug(db, slug)
    repo = TenantRepository(db, company.id)
    gallery = await repo.list_gallery_photos()
    rating = await get_rating_summary(db, company.id)
    return {
        "slug": company.booking_slug,
        "name": company.name,
        "city": company.city,
        "address": company.address,
        "phone": company.phone,
        "working_hours": _working_hours_from_dict(company.working_hours),
        "logo_url": public_media_url(company.photo_path),
        "gallery": [_gallery_photo_to_dict(photo) for photo in gallery],
        "rating_average": rating["average"],
        "rating_count": rating["count"],
    }

async def list_public_booking_members(db: AsyncSession, company: Company) -> list[dict]:
    repo = TenantRepository(db, company.id)
    result = await db.execute(
        select(CompanyMember)
        .options(
            selectinload(CompanyMember.user),
            selectinload(CompanyMember.role),
        )
        .where(CompanyMember.company_id == company.id)
        .order_by(CompanyMember.created_at)
    )
    members = list(result.scalars().all())
    bookable: list[dict] = []
    for member in members:
        schedules = await repo.list_member_schedules(member.id)
        services = await repo.list_services(active_only=True, member_id=member.id)
        if not schedules and not services:
            continue
        bookable.append(
            {
                "id": member.id,
                "full_name": member.user.full_name if member.user else "Специалист",
                "role_name": member.role.name if member.role else None,
                "photo_url": public_media_url(member.photo_path),
            }
        )
    return bookable


async def list_public_booking_services(
    db: AsyncSession,
    company: Company,
    *,
    member_id: UUID | None = None,
) -> list[dict]:
    repo = TenantRepository(db, company.id)
    if member_id is not None:
        member = await repo.get_member_by_id(member_id)
        if not member:
            raise NotFoundError("Специалист не найден")
    services = await repo.list_services(active_only=True, member_id=member_id)
    public_services: list[dict] = []
    for service in services:
        data = service_to_response(service)
        public_services.append(
            {
                "id": data["id"],
                "name": data["name"],
                "category": data["category"],
                "description": data["description"],
                "duration_minutes": data["duration_minutes"],
                "buffer_before_minutes": data["buffer_before_minutes"],
                "buffer_after_minutes": data["buffer_after_minutes"],
                "price": data["price"],
                "member_id": data["member_id"],
            }
        )
    return public_services


def _pick_schedule_for_day(
    schedules: list[MemberWorkSchedule], day: date
) -> MemberWorkSchedule | None:
    for schedule in schedules:
        if schedule.date_from <= day <= schedule.date_to:
            return schedule
    return None


async def get_public_booking_slots(
    db: AsyncSession,
    company: Company,
    member_id: UUID,
    *,
    service_id: UUID,
    from_date: date,
    to_date: date,
) -> dict:
    if to_date < from_date:
        raise AppError("to_date не может быть раньше from_date")
    if (to_date - from_date).days > 60:
        raise AppError("Период не более 60 дней")

    repo = TenantRepository(db, company.id)
    member = await repo.get_member_by_id(member_id)
    if not member:
        raise NotFoundError("Специалист не найден")

    service = await get_company_service(db, company.id, service_id)
    if not service.is_active:
        raise AppError("Услуга недоступна")
    if service.member_id is not None and service.member_id != member_id:
        raise AppError("Услуга недоступна у выбранного специалиста")

    schedules = await repo.list_member_schedules(member_id)
    exceptions = await list_schedule_exceptions(
        db, company.id, member_id, from_date=from_date, to_date=to_date
    )
    appointments = await repo.list_member_appointments(
        member_id,
        from_date=from_date,
        to_date=to_date,
        statuses=[AppointmentStatus.SCHEDULED],
    )

    slots_by_day: dict[str, list[str]] = {}
    current = from_date
    while current <= to_date:
        schedule = _pick_schedule_for_day(schedules, current)
        if schedule:
            day_slots = generate_slots_for_day(
                schedule,
                current,
                exceptions,
                appointments=appointments,
                booking_duration_minutes=service.duration_minutes,
                buffer_before_minutes=service.buffer_before_minutes,
                buffer_after_minutes=service.buffer_after_minutes,
            )
            if day_slots:
                slots_by_day[current.isoformat()] = [slot.strftime("%H:%M") for slot in day_slots]
        current += timedelta(days=1)

    return {
        "member_id": member_id,
        "service_id": service_id,
        "from_date": from_date,
        "to_date": to_date,
        "slots_by_day": slots_by_day,
    }


async def create_public_booking_appointment(
    db: AsyncSession,
    company: Company,
    member_id: UUID,
    *,
    service_id: UUID,
    starts_at,
    client_phone: str,
    client_name: str | None = None,
    client_full_name: str | None = None,
    client_email: str | None = None,
    note: str | None = None,
) -> dict:
    appointment = await create_appointment_for_company(
        db,
        company,
        member_id,
        service_id=service_id,
        starts_at=starts_at,
        client_phone=client_phone,
        client_name=client_name,
        client_full_name=client_full_name,
        client_email=client_email,
        note=note,
        created_by_id=None,
    )
    return public_appointment_to_response(appointment)
