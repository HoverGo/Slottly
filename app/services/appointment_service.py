from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.tenant import TenantContext
from app.models.entities import AppointmentStatus, CompanyService, MemberAppointment, MemberWorkSchedule
from app.repositories.tenant_repository import TenantRepository
from app.services.schedule_service import (
    generate_slots_for_day,
    get_appointment_end,
    list_schedule_exceptions,
    normalize_datetime,
)
from app.services.service_catalog_service import get_company_service


def appointment_to_response(appointment: MemberAppointment) -> dict:
    return {
        "id": appointment.id,
        "company_id": appointment.company_id,
        "member_id": appointment.member_id,
        "service_id": appointment.service_id,
        "service_name": appointment.service.name if appointment.service else None,
        "starts_at": appointment.starts_at,
        "duration_minutes": appointment.duration_minutes,
        "ends_at": get_appointment_end(appointment),
        "client_name": appointment.client_name,
        "client_phone": appointment.client_phone,
        "status": appointment.status.value,
        "note": appointment.note,
        "created_by_id": appointment.created_by_id,
        "created_at": appointment.created_at,
    }


async def _get_active_schedule_for_day(
    db: AsyncSession,
    company_id: UUID,
    member_id: UUID,
    day: date,
) -> MemberWorkSchedule | None:
    repo = TenantRepository(db, company_id)
    schedules = await repo.list_member_schedules(member_id)
    for schedule in schedules:
        if schedule.date_from <= day <= schedule.date_to:
            return schedule
    return None


async def _validate_appointment_slot(
    db: AsyncSession,
    company_id: UUID,
    member_id: UUID,
    service: CompanyService,
    starts_at: datetime,
    *,
    exclude_appointment_id: UUID | None = None,
) -> MemberWorkSchedule:
    if not service.is_active:
        raise AppError("Услуга неактивна")
    if service.member_id is not None and service.member_id != member_id:
        raise AppError("Услуга привязана к другому специалисту")

    day = starts_at.date()
    schedule = await _get_active_schedule_for_day(db, company_id, member_id, day)
    if not schedule:
        raise AppError("На выбранную дату нет расписания у специалиста")

    exceptions = await list_schedule_exceptions(db, company_id, member_id, from_date=day, to_date=day)
    repo = TenantRepository(db, company_id)
    appointments = await repo.list_member_appointments(
        member_id, from_date=day, to_date=day, statuses=[AppointmentStatus.SCHEDULED]
    )
    if exclude_appointment_id:
        appointments = [a for a in appointments if a.id != exclude_appointment_id]

    day_slots = generate_slots_for_day(
        schedule,
        day,
        exceptions,
        appointments=appointments,
        booking_duration_minutes=service.duration_minutes,
    )
    slot_key = normalize_datetime(starts_at)
    allowed = {normalize_datetime(s) for s in day_slots}
    if slot_key not in allowed:
        raise ConflictError("Выбранное время недоступно для записи на эту услугу")

    return schedule


async def create_appointment(
    db: AsyncSession,
    tenant: TenantContext,
    member_id: UUID,
    *,
    service_id: UUID,
    starts_at: datetime,
    client_name: str | None = None,
    client_phone: str | None = None,
    note: str | None = None,
) -> MemberAppointment:
    from app.services.company_service import require_active_subscription

    await require_active_subscription(db, tenant.company)

    repo = TenantRepository(db, tenant.company_id)
    member = await repo.get_member_by_id(member_id)
    if not member:
        raise NotFoundError("Сотрудник не найден в компании")

    service = await get_company_service(db, tenant.company_id, service_id)
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=UTC)

    await _validate_appointment_slot(db, tenant.company_id, member_id, service, starts_at)

    appointment = MemberAppointment(
        company_id=tenant.company_id,
        member_id=member.id,
        service_id=service.id,
        starts_at=starts_at,
        duration_minutes=service.duration_minutes,
        client_name=client_name,
        client_phone=client_phone,
        status=AppointmentStatus.SCHEDULED,
        note=note,
        created_by_id=tenant.user_id,
    )
    db.add(appointment)
    await db.flush()
    await db.refresh(appointment, ["service"])
    return appointment


async def list_member_appointments(
    db: AsyncSession,
    company_id: UUID,
    member_id: UUID,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
    status: AppointmentStatus | None = None,
) -> list[MemberAppointment]:
    repo = TenantRepository(db, company_id)
    member = await repo.get_member_by_id(member_id)
    if not member:
        raise NotFoundError("Сотрудник не найден в компании")

    statuses = [status] if status else None
    return await repo.list_member_appointments(
        member_id, from_date=from_date, to_date=to_date, statuses=statuses
    )


async def get_member_appointment(
    db: AsyncSession, company_id: UUID, member_id: UUID, appointment_id: UUID
) -> MemberAppointment:
    repo = TenantRepository(db, company_id)
    appointment = await repo.get_member_appointment(member_id, appointment_id)
    if not appointment:
        raise NotFoundError("Запись не найдена")
    return appointment


async def update_appointment(
    db: AsyncSession,
    tenant: TenantContext,
    member_id: UUID,
    appointment_id: UUID,
    *,
    status: AppointmentStatus | None = None,
    client_name: str | None = None,
    client_phone: str | None = None,
    note: str | None = None,
) -> MemberAppointment:
    from app.services.company_service import require_active_subscription

    await require_active_subscription(db, tenant.company)

    appointment = await get_member_appointment(db, tenant.company_id, member_id, appointment_id)

    if status is not None:
        appointment.status = status
    if client_name is not None:
        appointment.client_name = client_name
    if client_phone is not None:
        appointment.client_phone = client_phone
    if note is not None:
        appointment.note = note

    await db.flush()
    await db.refresh(appointment, ["service"])
    return appointment


async def cancel_appointment(
    db: AsyncSession,
    tenant: TenantContext,
    member_id: UUID,
    appointment_id: UUID,
) -> MemberAppointment:
    return await update_appointment(
        db,
        tenant,
        member_id,
        appointment_id,
        status=AppointmentStatus.CANCELLED,
    )
