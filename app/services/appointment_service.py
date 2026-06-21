from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.tenant import TenantContext
from app.models.entities import AppointmentStatus, Company, CompanyService, MemberAppointment, MemberWorkSchedule
from app.repositories.tenant_repository import TenantRepository
from app.services.client_service import format_phone_display, get_or_create_client
from app.services.schedule_service import (
    generate_slots_for_day,
    get_appointment_end,
    list_schedule_exceptions,
    normalize_datetime,
)
from app.services.service_catalog_service import get_company_service


def appointment_to_response(appointment: MemberAppointment) -> dict:
    member_user = appointment.member.user if appointment.member else None
    return {
        "id": appointment.id,
        "company_id": appointment.company_id,
        "member_id": appointment.member_id,
        "member_name": member_user.full_name if member_user else None,
        "service_id": appointment.service_id,
        "service_name": appointment.service.name if appointment.service else None,
        "starts_at": appointment.starts_at,
        "duration_minutes": appointment.duration_minutes,
        "ends_at": get_appointment_end(appointment),
        "client_id": appointment.client_id,
        "client_name": appointment.client_name,
        "client_full_name": appointment.client_full_name,
        "client_phone": appointment.client_phone,
        "client_email": appointment.client_email,
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
        buffer_before_minutes=service.buffer_before_minutes,
        buffer_after_minutes=service.buffer_after_minutes,
    )
    slot_key = normalize_datetime(starts_at)
    allowed = {normalize_datetime(s) for s in day_slots}
    if slot_key not in allowed:
        raise ConflictError("Выбранное время недоступно для записи на эту услугу")

    return schedule


def public_appointment_to_response(appointment: MemberAppointment) -> dict:
    member_user = appointment.member.user if appointment.member else None
    return {
        "id": appointment.id,
        "member_id": appointment.member_id,
        "member_name": member_user.full_name if member_user else None,
        "service_id": appointment.service_id,
        "service_name": appointment.service.name if appointment.service else None,
        "starts_at": appointment.starts_at,
        "ends_at": get_appointment_end(appointment),
        "duration_minutes": appointment.duration_minutes,
        "status": appointment.status.value,
    }


async def create_appointment_for_company(
    db: AsyncSession,
    company: Company,
    member_id: UUID,
    *,
    service_id: UUID,
    starts_at: datetime,
    client_phone: str,
    client_name: str | None = None,
    client_full_name: str | None = None,
    client_email: str | None = None,
    note: str | None = None,
    created_by_id: UUID | None = None,
) -> MemberAppointment:
    from app.services.company_service import check_subscription_limit, require_active_subscription

    await require_active_subscription(db, company)
    await check_subscription_limit(db, company, add_appointments=1)

    repo = TenantRepository(db, company.id)
    member = await repo.get_member_by_id(member_id)
    if not member:
        raise NotFoundError("Сотрудник не найден в компании")

    service = await get_company_service(db, company.id, service_id)
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=UTC)

    await _validate_appointment_slot(db, company.id, member_id, service, starts_at)

    client = await get_or_create_client(
        db,
        company.id,
        phone=client_phone,
        name=client_name,
        full_name=client_full_name,
        email=client_email,
    )

    appointment = MemberAppointment(
        company_id=company.id,
        member_id=member.id,
        service_id=service.id,
        client_id=client.id,
        starts_at=starts_at,
        duration_minutes=service.duration_minutes,
        buffer_before_minutes=service.buffer_before_minutes,
        buffer_after_minutes=service.buffer_after_minutes,
        client_name=client_name,
        client_full_name=client_full_name,
        client_phone=format_phone_display(client_phone),
        client_email=client_email,
        status=AppointmentStatus.SCHEDULED,
        note=note,
        created_by_id=created_by_id,
    )
    db.add(appointment)
    await db.flush()
    await db.refresh(appointment, ["service", "member"])
    if appointment.member:
        await db.refresh(appointment.member, ["user"])
    return appointment


async def create_appointment(
    db: AsyncSession,
    tenant: TenantContext,
    member_id: UUID,
    *,
    service_id: UUID,
    starts_at: datetime,
    client_phone: str,
    client_name: str | None = None,
    client_full_name: str | None = None,
    client_email: str | None = None,
    note: str | None = None,
) -> MemberAppointment:
    return await create_appointment_for_company(
        db,
        tenant.company,
        member_id,
        service_id=service_id,
        starts_at=starts_at,
        client_phone=client_phone,
        client_name=client_name,
        client_full_name=client_full_name,
        client_email=client_email,
        note=note,
        created_by_id=tenant.user_id,
    )


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
    await db.refresh(appointment, ["service", "member"])
    if appointment.member:
        await db.refresh(appointment.member, ["user"])
    return appointment


async def update_appointment(
    db: AsyncSession,
    tenant: TenantContext,
    member_id: UUID,
    appointment_id: UUID,
    *,
    status: AppointmentStatus | None = None,
    client_name: str | None = None,
    client_full_name: str | None = None,
    client_phone: str | None = None,
    client_email: str | None = None,
    note: str | None = None,
) -> MemberAppointment:
    from app.services.company_service import require_active_subscription

    await require_active_subscription(db, tenant.company)

    appointment = await get_member_appointment(db, tenant.company_id, member_id, appointment_id)

    if status is not None:
        appointment.status = status
    if client_name is not None:
        appointment.client_name = client_name
    if client_full_name is not None:
        appointment.client_full_name = client_full_name
    if client_email is not None:
        appointment.client_email = client_email
    if note is not None:
        appointment.note = note

    if client_phone is not None:
        client = await get_or_create_client(
            db,
            tenant.company_id,
            phone=client_phone,
            name=appointment.client_name,
            full_name=appointment.client_full_name,
            email=appointment.client_email,
        )
        appointment.client_id = client.id
        appointment.client_phone = format_phone_display(client_phone)
    elif appointment.client_id and (
        client_name is not None or client_full_name is not None or client_email is not None
    ):
        client = await get_or_create_client(
            db,
            tenant.company_id,
            phone=appointment.client_phone or "",
            name=appointment.client_name,
            full_name=appointment.client_full_name,
            email=appointment.client_email,
        )
        appointment.client_id = client.id

    await db.flush()
    await db.refresh(appointment, ["service", "member"])
    if appointment.member:
        await db.refresh(appointment.member, ["user"])
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
