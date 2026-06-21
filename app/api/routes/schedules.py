from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_company_tenant, require_permission
from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.permissions import MANAGE_SCHEDULES
from app.core.tenant import TenantContext
from app.models.entities import ScheduleExceptionKind
from app.schemas.schedules import (
    ScheduleExceptionCreate,
    ScheduleExceptionResponse,
    WorkScheduleCreate,
    WorkScheduleResponse,
    WorkScheduleSlotsResponse,
)
from app.services.schedule_service import (
    create_schedule_exception,
    create_work_schedule,
    delete_schedule_exception,
    generate_slots_range,
    get_member_schedule,
    list_member_schedules,
    list_schedule_exceptions,
)
from app.services.service_catalog_service import get_company_service
from app.repositories.tenant_repository import TenantRepository

router = APIRouter(prefix="/companies/{company_id}/members", tags=["schedules"])


@router.post("/{member_id}/schedules", response_model=WorkScheduleResponse, status_code=201)
async def create_schedule(
    member_id: UUID,
    data: WorkScheduleCreate,
    tenant: TenantContext = Depends(require_permission(MANAGE_SCHEDULES)),
    db: AsyncSession = Depends(get_db),
) -> WorkScheduleResponse:
    try:
        schedule = await create_work_schedule(
            db,
            tenant,
            member_id,
            date_from=data.date_from,
            date_to=data.date_to,
            time_start=data.time_start,
            time_end=data.time_end,
            slot_interval_minutes=data.slot_interval_minutes,
            pattern_type=data.pattern_type,
            pattern_config=data.pattern_config,
        )
        return WorkScheduleResponse.model_validate(schedule)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/{member_id}/schedules", response_model=list[WorkScheduleResponse])
async def list_schedules(
    member_id: UUID,
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[WorkScheduleResponse]:
    try:
        schedules = await list_member_schedules(db, tenant.company_id, member_id)
        return [WorkScheduleResponse.model_validate(s) for s in schedules]
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/{member_id}/schedules/{schedule_id}/slots", response_model=WorkScheduleSlotsResponse)
async def get_schedule_slots(
    member_id: UUID,
    schedule_id: UUID,
    from_date: date = Query(..., description="Начало периода"),
    to_date: date = Query(..., description="Конец периода"),
    service_id: UUID | None = Query(default=None, description="Услуга для расчёта занятости слотов"),
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
) -> WorkScheduleSlotsResponse:
    try:
        schedule = await get_member_schedule(db, tenant.company_id, member_id, schedule_id)
        exceptions = await list_schedule_exceptions(
            db, tenant.company_id, member_id, from_date=from_date, to_date=to_date
        )
        repo = TenantRepository(db, tenant.company_id)
        appointments = await repo.list_member_appointments(
            member_id, from_date=from_date, to_date=to_date, statuses=None
        )

        booking_duration: int | None = None
        if service_id is not None:
            service = await get_company_service(db, tenant.company_id, service_id)
            if service.member_id is not None and service.member_id != member_id:
                raise AppError("Услуга привязана к другому специалисту")
            booking_duration = service.duration_minutes

        slots = generate_slots_range(
            schedule,
            from_date,
            to_date,
            exceptions,
            appointments=appointments,
            booking_duration_minutes=booking_duration,
        )
        return WorkScheduleSlotsResponse(
            schedule_id=schedule.id,
            member_id=member_id,
            from_date=from_date,
            to_date=to_date,
            service_id=service_id,
            booking_duration_minutes=booking_duration,
            slots_by_day=slots,
        )
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post(
    "/{member_id}/schedule-exceptions",
    response_model=ScheduleExceptionResponse,
    status_code=201,
)
async def create_schedule_exception_endpoint(
    member_id: UUID,
    data: ScheduleExceptionCreate,
    tenant: TenantContext = Depends(require_permission(MANAGE_SCHEDULES)),
    db: AsyncSession = Depends(get_db),
) -> ScheduleExceptionResponse:
    try:
        exception = await create_schedule_exception(
            db,
            tenant,
            member_id,
            kind=ScheduleExceptionKind(data.kind),
            block_config=data.block_config,
            note=data.note,
            exception_date=data.exception_date,
            date_from=data.date_from,
            date_to=data.date_to,
            dates=data.dates,
        )
        return ScheduleExceptionResponse.model_validate(exception)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get(
    "/{member_id}/schedule-exceptions",
    response_model=list[ScheduleExceptionResponse],
)
async def list_schedule_exceptions_endpoint(
    member_id: UUID,
    from_date: date | None = Query(default=None, description="Начало периода"),
    to_date: date | None = Query(default=None, description="Конец периода"),
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[ScheduleExceptionResponse]:
    try:
        exceptions = await list_schedule_exceptions(
            db, tenant.company_id, member_id, from_date=from_date, to_date=to_date
        )
        return [ScheduleExceptionResponse.model_validate(e) for e in exceptions]
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.delete("/{member_id}/schedule-exceptions/{exception_id}", status_code=204)
async def delete_schedule_exception_endpoint(
    member_id: UUID,
    exception_id: UUID,
    tenant: TenantContext = Depends(require_permission(MANAGE_SCHEDULES)),
    db: AsyncSession = Depends(get_db),
) -> None:
    try:
        await delete_schedule_exception(db, tenant, member_id, exception_id)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
