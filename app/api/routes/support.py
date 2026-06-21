from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.exceptions import AppError
from app.models.entities import User
from app.schemas.support import (
    SupportMessageCreate,
    SupportMessageResponse,
    SupportTicketCreate,
    SupportTicketDetailResponse,
    SupportTicketResponse,
)
from app.services.support_service import (
    _message_to_response,
    _ticket_to_response,
    add_user_message,
    create_ticket,
    get_user_ticket,
    list_user_tickets,
)

router = APIRouter(prefix="/support", tags=["support"])


def _ticket_response(ticket, *, detail: bool = False):
    base = _ticket_to_response(ticket, include_user=True)
    if not detail:
        return SupportTicketResponse(**base)
    messages = [_message_to_response(m) for m in ticket.messages]
    return SupportTicketDetailResponse(**base, messages=[SupportMessageResponse(**m) for m in messages])


@router.post("/tickets", response_model=SupportTicketDetailResponse, status_code=201)
async def create_support_ticket(
    data: SupportTicketCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SupportTicketDetailResponse:
    try:
        ticket = await create_ticket(
            db, current_user, subject=data.subject, message=data.message
        )
        return _ticket_response(ticket, detail=True)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/tickets", response_model=list[SupportTicketResponse])
async def list_my_tickets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SupportTicketResponse]:
    tickets = await list_user_tickets(db, current_user.id)
    return [SupportTicketResponse(**_ticket_to_response(t, include_user=False)) for t in tickets]


@router.get("/tickets/{ticket_id}", response_model=SupportTicketDetailResponse)
async def get_my_ticket(
    ticket_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SupportTicketDetailResponse:
    try:
        ticket = await get_user_ticket(db, current_user.id, ticket_id)
        return _ticket_response(ticket, detail=True)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/tickets/{ticket_id}/messages", response_model=SupportMessageResponse, status_code=201)
async def reply_to_ticket(
    ticket_id: UUID,
    data: SupportMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SupportMessageResponse:
    try:
        message = await add_user_message(db, current_user, ticket_id, data.body)
        return SupportMessageResponse(**_message_to_response(message))
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
