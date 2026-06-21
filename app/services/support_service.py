from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppError, ForbiddenError, NotFoundError
from app.core.platform_roles import user_is_platform_staff
from app.models.entities import SupportTicket, SupportTicketMessage, SupportTicketStatus, User


CLOSED_STATUSES = frozenset({SupportTicketStatus.RESOLVED, SupportTicketStatus.CLOSED})


def _ticket_to_response(ticket: SupportTicket, *, include_user: bool = False) -> dict:
    data = {
        "id": ticket.id,
        "user_id": ticket.user_id,
        "subject": ticket.subject,
        "status": ticket.status,
        "assigned_to_id": ticket.assigned_to_id,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "closed_at": ticket.closed_at,
        "messages_count": len(ticket.messages) if ticket.messages is not None else 0,
    }
    if include_user or ticket.user:
        data["user_email"] = ticket.user.email if ticket.user else None
        data["user_name"] = ticket.user.full_name if ticket.user else None
    if ticket.assigned_to:
        data["assigned_to_name"] = ticket.assigned_to.full_name
    return data


def _message_to_response(message: SupportTicketMessage) -> dict:
    return {
        "id": message.id,
        "ticket_id": message.ticket_id,
        "author_id": message.author_id,
        "author_name": message.author.full_name if message.author else None,
        "author_email": message.author.email if message.author else None,
        "body": message.body,
        "is_staff_reply": message.is_staff_reply,
        "created_at": message.created_at,
    }


async def _get_ticket_with_relations(db: AsyncSession, ticket_id: UUID) -> SupportTicket | None:
    result = await db.execute(
        select(SupportTicket)
        .options(
            selectinload(SupportTicket.user),
            selectinload(SupportTicket.assigned_to),
            selectinload(SupportTicket.messages).selectinload(SupportTicketMessage.author),
        )
        .where(SupportTicket.id == ticket_id)
    )
    return result.scalar_one_or_none()


async def create_ticket(db: AsyncSession, user: User, *, subject: str, message: str) -> SupportTicket:
    ticket = SupportTicket(
        user_id=user.id,
        subject=subject,
        status=SupportTicketStatus.OPEN,
    )
    db.add(ticket)
    await db.flush()

    first_message = SupportTicketMessage(
        ticket_id=ticket.id,
        author_id=user.id,
        body=message,
        is_staff_reply=False,
    )
    db.add(first_message)
    await db.flush()

    loaded = await _get_ticket_with_relations(db, ticket.id)
    assert loaded is not None
    return loaded


async def list_user_tickets(db: AsyncSession, user_id: UUID) -> list[SupportTicket]:
    result = await db.execute(
        select(SupportTicket)
        .options(
            selectinload(SupportTicket.user),
            selectinload(SupportTicket.assigned_to),
            selectinload(SupportTicket.messages),
        )
        .where(SupportTicket.user_id == user_id)
        .order_by(SupportTicket.updated_at.desc())
    )
    return list(result.scalars().all())


async def get_user_ticket(db: AsyncSession, user_id: UUID, ticket_id: UUID) -> SupportTicket:
    ticket = await _get_ticket_with_relations(db, ticket_id)
    if not ticket or ticket.user_id != user_id:
        raise NotFoundError("Обращение не найдено")
    return ticket


async def add_user_message(
    db: AsyncSession, user: User, ticket_id: UUID, body: str
) -> SupportTicketMessage:
    ticket = await get_user_ticket(db, user.id, ticket_id)
    if ticket.status in CLOSED_STATUSES:
        raise AppError("Обращение закрыто, новые сообщения недоступны")

    msg = SupportTicketMessage(
        ticket_id=ticket.id,
        author_id=user.id,
        body=body,
        is_staff_reply=False,
    )
    ticket.status = SupportTicketStatus.OPEN
    ticket.updated_at = datetime.now(UTC)
    db.add(msg)
    await db.flush()
    await db.refresh(msg, ["author"])
    return msg


async def list_all_tickets(
    db: AsyncSession,
    *,
    status: SupportTicketStatus | None = None,
    assigned_to_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[SupportTicket]:
    query = (
        select(SupportTicket)
        .options(
            selectinload(SupportTicket.user),
            selectinload(SupportTicket.assigned_to),
            selectinload(SupportTicket.messages),
        )
        .order_by(SupportTicket.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if status is not None:
        query = query.where(SupportTicket.status == status)
    if assigned_to_id is not None:
        query = query.where(SupportTicket.assigned_to_id == assigned_to_id)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_ticket_for_staff(db: AsyncSession, ticket_id: UUID) -> SupportTicket:
    ticket = await _get_ticket_with_relations(db, ticket_id)
    if not ticket:
        raise NotFoundError("Обращение не найдено")
    return ticket


async def update_ticket_by_staff(
    db: AsyncSession,
    ticket_id: UUID,
    *,
    status: SupportTicketStatus | None = None,
    assigned_to_id: UUID | None = None,
    clear_assignment: bool = False,
) -> SupportTicket:
    ticket = await get_ticket_for_staff(db, ticket_id)

    if status is not None:
        ticket.status = status
        if status in CLOSED_STATUSES:
            ticket.closed_at = datetime.now(UTC)
        elif ticket.closed_at is not None:
            ticket.closed_at = None

    if clear_assignment:
        ticket.assigned_to_id = None
    elif assigned_to_id is not None:
        assignee = await db.get(User, assigned_to_id)
        if not assignee or not user_is_platform_staff(assignee):
            raise AppError("Назначить можно только сотрудника техподдержки или администратора")
        ticket.assigned_to_id = assigned_to_id
        if ticket.status == SupportTicketStatus.OPEN:
            ticket.status = SupportTicketStatus.IN_PROGRESS

    ticket.updated_at = datetime.now(UTC)
    await db.flush()
    return await get_ticket_for_staff(db, ticket_id)


async def add_staff_message(
    db: AsyncSession, staff: User, ticket_id: UUID, body: str
) -> SupportTicketMessage:
    if not user_is_platform_staff(staff):
        raise ForbiddenError("Нет прав техподдержки")

    ticket = await get_ticket_for_staff(db, ticket_id)
    if ticket.status in CLOSED_STATUSES:
        raise AppError("Обращение закрыто")

    msg = SupportTicketMessage(
        ticket_id=ticket.id,
        author_id=staff.id,
        body=body,
        is_staff_reply=True,
    )
    if ticket.assigned_to_id is None:
        ticket.assigned_to_id = staff.id
    ticket.status = SupportTicketStatus.WAITING_USER
    ticket.updated_at = datetime.now(UTC)

    db.add(msg)
    await db.flush()
    await db.refresh(msg, ["author"])
    return msg


async def count_open_tickets(db: AsyncSession) -> int:
    result = await db.scalar(
        select(func.count())
        .select_from(SupportTicket)
        .where(
            SupportTicket.status.in_(
                [
                    SupportTicketStatus.OPEN,
                    SupportTicketStatus.IN_PROGRESS,
                    SupportTicketStatus.WAITING_USER,
                ]
            )
        )
    )
    return result or 0
