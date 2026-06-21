from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_company_tenant, require_permission
from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.permissions import MANAGE_SERVICES
from app.core.tenant import TenantContext
from app.models.entities import AppointmentStatus
from app.schemas.services import (
    AppointmentCreate,
    AppointmentResponse,
    AppointmentUpdate,
    ClientAppointmentHistoryItem,
    ClientHistoryResponse,
    CompanyClientResponse,
    CompanyServiceCreate,
    CompanyServiceResponse,
    CompanyServiceUpdate,
)
from app.services.appointment_service import (
    appointment_to_response,
    cancel_appointment,
    create_appointment,
    get_member_appointment,
    list_member_appointments,
    update_appointment,
)
from app.services.client_service import (
    appointment_history_item,
    client_to_dict,
    count_client_appointments,
    get_client_by_id,
    get_client_by_phone,
    list_client_appointments,
)
from app.services.service_catalog_service import (
    create_company_service,
    get_company_service,
    list_company_services,
    service_to_response,
    update_company_service,
)

router = APIRouter(prefix="/companies/{company_id}", tags=["services"])


@router.post("/services", response_model=CompanyServiceResponse, status_code=201)
async def create_service(
    data: CompanyServiceCreate,
    tenant: TenantContext = Depends(require_permission(MANAGE_SERVICES)),
    db: AsyncSession = Depends(get_db),
) -> CompanyServiceResponse:
    try:
        service = await create_company_service(
            db,
            tenant,
            name=data.name,
            category=data.category,
            description=data.description,
            duration_minutes=data.duration_minutes,
            buffer_before_minutes=data.buffer_before_minutes,
            buffer_after_minutes=data.buffer_after_minutes,
            price=data.price,
            member_id=data.member_id,
            branch_id=data.branch_id,
        )
        return CompanyServiceResponse(**service_to_response(service))
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/services", response_model=list[CompanyServiceResponse])
async def list_services(
    active_only: bool = Query(default=False),
    member_id: UUID | None = Query(default=None),
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[CompanyServiceResponse]:
    services = await list_company_services(
        db, tenant.company_id, active_only=active_only, member_id=member_id
    )
    return [CompanyServiceResponse(**service_to_response(s)) for s in services]


@router.get("/services/{service_id}", response_model=CompanyServiceResponse)
async def get_service(
    service_id: UUID,
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
) -> CompanyServiceResponse:
    try:
        service = await get_company_service(db, tenant.company_id, service_id)
        return CompanyServiceResponse(**service_to_response(service))
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.patch("/services/{service_id}", response_model=CompanyServiceResponse)
async def update_service(
    service_id: UUID,
    data: CompanyServiceUpdate,
    tenant: TenantContext = Depends(require_permission(MANAGE_SERVICES)),
    db: AsyncSession = Depends(get_db),
) -> CompanyServiceResponse:
    try:
        service = await update_company_service(
            db,
            tenant,
            service_id,
            name=data.name,
            category=data.category,
            description=data.description,
            duration_minutes=data.duration_minutes,
            buffer_before_minutes=data.buffer_before_minutes,
            buffer_after_minutes=data.buffer_after_minutes,
            price=data.price,
            member_id=data.member_id,
            branch_id=data.branch_id,
            is_active=data.is_active,
            clear_member=data.clear_member,
            clear_branch=data.clear_branch,
            clear_category=data.clear_category,
        )
        return CompanyServiceResponse(**service_to_response(service))
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post(
    "/members/{member_id}/appointments",
    response_model=AppointmentResponse,
    status_code=201,
)
async def create_member_appointment(
    member_id: UUID,
    data: AppointmentCreate,
    tenant: TenantContext = Depends(require_permission(MANAGE_SERVICES)),
    db: AsyncSession = Depends(get_db),
) -> AppointmentResponse:
    try:
        appointment = await create_appointment(
            db,
            tenant,
            member_id,
            service_id=data.service_id,
            starts_at=data.starts_at,
            client_name=data.client_name,
            client_full_name=data.client_full_name,
            client_phone=data.client_phone,
            client_email=str(data.client_email) if data.client_email else None,
            note=data.note,
        )
        return AppointmentResponse(**appointment_to_response(appointment))
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/members/{member_id}/appointments", response_model=list[AppointmentResponse])
async def list_appointments(
    member_id: UUID,
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    status: AppointmentStatus | None = Query(default=None),
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[AppointmentResponse]:
    try:
        appointments = await list_member_appointments(
            db,
            tenant.company_id,
            member_id,
            from_date=from_date,
            to_date=to_date,
            status=status,
        )
        return [AppointmentResponse(**appointment_to_response(a)) for a in appointments]
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/members/{member_id}/appointments/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    member_id: UUID,
    appointment_id: UUID,
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
) -> AppointmentResponse:
    try:
        appointment = await get_member_appointment(
            db, tenant.company_id, member_id, appointment_id
        )
        return AppointmentResponse(**appointment_to_response(appointment))
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.patch("/members/{member_id}/appointments/{appointment_id}", response_model=AppointmentResponse)
async def patch_appointment(
    member_id: UUID,
    appointment_id: UUID,
    data: AppointmentUpdate,
    tenant: TenantContext = Depends(require_permission(MANAGE_SERVICES)),
    db: AsyncSession = Depends(get_db),
) -> AppointmentResponse:
    try:
        status = AppointmentStatus(data.status) if data.status else None
        appointment = await update_appointment(
            db,
            tenant,
            member_id,
            appointment_id,
            status=status,
            client_name=data.client_name,
            client_full_name=data.client_full_name,
            client_phone=data.client_phone,
            client_email=str(data.client_email) if data.client_email else None,
            note=data.note,
        )
        return AppointmentResponse(**appointment_to_response(appointment))
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.delete("/members/{member_id}/appointments/{appointment_id}", response_model=AppointmentResponse)
async def delete_appointment(
    member_id: UUID,
    appointment_id: UUID,
    tenant: TenantContext = Depends(require_permission(MANAGE_SERVICES)),
    db: AsyncSession = Depends(get_db),
) -> AppointmentResponse:
    try:
        appointment = await cancel_appointment(db, tenant, member_id, appointment_id)
        return AppointmentResponse(**appointment_to_response(appointment))
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/clients/lookup", response_model=CompanyClientResponse)
async def lookup_client_by_phone(
    phone: str = Query(..., min_length=5, max_length=50),
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
) -> CompanyClientResponse:
    try:
        client = await get_client_by_phone(db, tenant.company_id, phone)
        count = await count_client_appointments(db, tenant.company_id, client.id)
        return CompanyClientResponse(**client_to_dict(client, appointments_count=count))
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/clients/history", response_model=ClientHistoryResponse)
async def get_client_history_by_phone(
    phone: str = Query(..., min_length=5, max_length=50),
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
) -> ClientHistoryResponse:
    try:
        client = await get_client_by_phone(db, tenant.company_id, phone)
        appointments = await list_client_appointments(db, tenant.company_id, client.id)
        return ClientHistoryResponse(
            client=CompanyClientResponse(**client_to_dict(client, appointments_count=len(appointments))),
            appointments=[
                ClientAppointmentHistoryItem(**appointment_history_item(item)) for item in appointments
            ],
        )
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/clients/{client_id}/history", response_model=ClientHistoryResponse)
async def get_client_history(
    client_id: UUID,
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
) -> ClientHistoryResponse:
    try:
        client = await get_client_by_id(db, tenant.company_id, client_id)
        appointments = await list_client_appointments(db, tenant.company_id, client.id)
        return ClientHistoryResponse(
            client=CompanyClientResponse(**client_to_dict(client, appointments_count=len(appointments))),
            appointments=[
                ClientAppointmentHistoryItem(**appointment_history_item(item)) for item in appointments
            ],
        )
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
