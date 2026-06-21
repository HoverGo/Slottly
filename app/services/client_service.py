import re
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, NotFoundError
from app.models.entities import CompanyClient, MemberAppointment
from app.repositories.tenant_repository import TenantRepository
from app.services.schedule_service import get_appointment_end


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone.strip())
    if not digits:
        raise AppError("Укажите номер телефона")
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    elif len(digits) == 10:
        digits = "7" + digits
    if len(digits) < 10 or len(digits) > 15:
        raise AppError("Некорректный номер телефона")
    return digits


def format_phone_display(phone: str) -> str:
    normalized = normalize_phone(phone)
    if len(normalized) == 11 and normalized.startswith("7"):
        return f"+7 ({normalized[1:4]}) {normalized[4:7]}-{normalized[7:9]}-{normalized[9:11]}"
    return phone.strip()


def validate_client_contact(
    *,
    name: str | None,
    full_name: str | None,
    phone: str | None,
    email: str | None = None,
) -> tuple[str, str, str | None, str | None, str | None]:
    if not phone or not phone.strip():
        raise AppError("Номер телефона обязателен")
    normalized = normalize_phone(phone)
    display = format_phone_display(phone)
    clean_name = name.strip() if name and name.strip() else None
    clean_full_name = full_name.strip() if full_name and full_name.strip() else None
    if not clean_name and not clean_full_name:
        raise AppError("Укажите имя или ФИО клиента")
    clean_email = email.strip().lower() if email and email.strip() else None
    return normalized, display, clean_name, clean_full_name, clean_email


async def get_or_create_client(
    db: AsyncSession,
    company_id: UUID,
    *,
    phone: str,
    name: str | None = None,
    full_name: str | None = None,
    email: str | None = None,
) -> CompanyClient:
    normalized, display, clean_name, clean_full_name, clean_email = validate_client_contact(
        name=name, full_name=full_name, phone=phone, email=email
    )

    result = await db.execute(
        select(CompanyClient).where(
            CompanyClient.company_id == company_id,
            CompanyClient.phone_normalized == normalized,
        )
    )
    client = result.scalar_one_or_none()
    if client:
        if clean_name:
            client.name = clean_name
        if clean_full_name:
            client.full_name = clean_full_name
        if clean_email:
            client.email = clean_email
        client.phone_display = display
        client.updated_at = datetime.now(UTC)
        await db.flush()
        return client

    client = CompanyClient(
        company_id=company_id,
        phone_normalized=normalized,
        phone_display=display,
        name=clean_name,
        full_name=clean_full_name,
        email=clean_email,
    )
    db.add(client)
    await db.flush()
    return client


async def get_client_by_phone(db: AsyncSession, company_id: UUID, phone: str) -> CompanyClient:
    normalized = normalize_phone(phone)
    result = await db.execute(
        select(CompanyClient).where(
            CompanyClient.company_id == company_id,
            CompanyClient.phone_normalized == normalized,
        )
    )
    client = result.scalar_one_or_none()
    if not client:
        raise NotFoundError("Клиент с таким телефоном не найден")
    return client


async def get_client_by_id(db: AsyncSession, company_id: UUID, client_id: UUID) -> CompanyClient:
    result = await db.execute(
        select(CompanyClient).where(
            CompanyClient.id == client_id,
            CompanyClient.company_id == company_id,
        )
    )
    client = result.scalar_one_or_none()
    if not client:
        raise NotFoundError("Клиент не найден")
    return client


async def count_client_appointments(db: AsyncSession, company_id: UUID, client_id: UUID) -> int:
    result = await db.scalar(
        select(func.count())
        .select_from(MemberAppointment)
        .where(
            MemberAppointment.company_id == company_id,
            MemberAppointment.client_id == client_id,
        )
    )
    return result or 0


async def list_client_appointments(
    db: AsyncSession, company_id: UUID, client_id: UUID
) -> list[MemberAppointment]:
    await get_client_by_id(db, company_id, client_id)
    repo = TenantRepository(db, company_id)
    return await repo.list_client_appointments(client_id)


def client_to_dict(client: CompanyClient, *, appointments_count: int | None = None) -> dict:
    data = {
        "id": client.id,
        "company_id": client.company_id,
        "phone": client.phone_display,
        "phone_normalized": client.phone_normalized,
        "name": client.name,
        "full_name": client.full_name,
        "email": client.email,
        "created_at": client.created_at,
        "updated_at": client.updated_at,
    }
    if appointments_count is not None:
        data["appointments_count"] = appointments_count
    return data


def appointment_history_item(appointment: MemberAppointment) -> dict:
    member_user = appointment.member.user if appointment.member else None
    branch = appointment.service.branch if appointment.service else None
    return {
        "id": appointment.id,
        "service_id": appointment.service_id,
        "service_name": appointment.service.name if appointment.service else None,
        "member_id": appointment.member_id,
        "member_name": member_user.full_name if member_user else None,
        "branch_id": branch.id if branch else None,
        "branch_name": branch.name if branch else None,
        "starts_at": appointment.starts_at,
        "ends_at": get_appointment_end(appointment),
        "duration_minutes": appointment.duration_minutes,
        "status": appointment.status.value,
        "client_name": appointment.client_name,
        "client_full_name": appointment.client_full_name,
        "client_phone": appointment.client_phone,
        "client_email": appointment.client_email,
        "note": appointment.note,
        "created_at": appointment.created_at,
    }
