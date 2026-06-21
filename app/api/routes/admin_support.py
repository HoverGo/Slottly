from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_platform_staff
from app.core.database import get_db
from app.core.exceptions import AppError
from app.models.entities import SupportTicketStatus, User
from app.schemas.support import (
    SupportMessageCreate,
    SupportMessageResponse,
    SupportTicketDetailResponse,
    SupportTicketResponse,
    SupportTicketUpdate,
)
from app.services.support_service import (
    _message_to_response,
    _ticket_to_response,
    add_staff_message,
    get_ticket_for_staff,
    list_all_tickets,
    update_ticket_by_staff,
)

router = APIRouter(prefix="/admin/support", tags=["admin-support"])


def _ticket_response(ticket, *, detail: bool = False):
    base = _ticket_to_response(ticket, include_user=True)
    if not detail:
        return SupportTicketResponse(**base)
    messages = [_message_to_response(m) for m in ticket.messages]
    return SupportTicketDetailResponse(**base, messages=[SupportMessageResponse(**m) for m in messages])


@router.get("/tickets", response_model=list[SupportTicketResponse])
async def staff_list_tickets(
    status: SupportTicketStatus | None = Query(default=None),
    assigned_to_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_platform_staff),
    db: AsyncSession = Depends(get_db),
) -> list[SupportTicketResponse]:
    tickets = await list_all_tickets(
        db, status=status, assigned_to_id=assigned_to_id, limit=limit, offset=offset
    )
    return [SupportTicketResponse(**_ticket_to_response(t, include_user=True)) for t in tickets]


@router.get("/tickets/{ticket_id}", response_model=SupportTicketDetailResponse)
async def staff_get_ticket(
    ticket_id: UUID,
    _: User = Depends(require_platform_staff),
    db: AsyncSession = Depends(get_db),
) -> SupportTicketDetailResponse:
    try:
        ticket = await get_ticket_for_staff(db, ticket_id)
        return _ticket_response(ticket, detail=True)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.patch("/tickets/{ticket_id}", response_model=SupportTicketDetailResponse)
async def staff_update_ticket(
    ticket_id: UUID,
    data: SupportTicketUpdate,
    _: User = Depends(require_platform_staff),
    db: AsyncSession = Depends(get_db),
) -> SupportTicketDetailResponse:
    try:
        ticket = await update_ticket_by_staff(
            db,
            ticket_id,
            status=data.status,
            assigned_to_id=data.assigned_to_id,
            clear_assignment=data.clear_assignment,
        )
        return _ticket_response(ticket, detail=True)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/tickets/{ticket_id}/messages", response_model=SupportMessageResponse, status_code=201)
async def staff_reply_to_ticket(
    ticket_id: UUID,
    data: SupportMessageCreate,
    staff: User = Depends(require_platform_staff),
    db: AsyncSession = Depends(get_db),
) -> SupportMessageResponse:
    try:
        message = await add_staff_message(db, staff, ticket_id, data.body)
        return SupportMessageResponse(**_message_to_response(message))
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
