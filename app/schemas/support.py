from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.entities import SupportTicketStatus


class SupportTicketCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1, max_length=10000)


class SupportMessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10000)


class SupportTicketUpdate(BaseModel):
    status: SupportTicketStatus | None = None
    assigned_to_id: UUID | None = None
    clear_assignment: bool = False


class SupportMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ticket_id: UUID
    author_id: UUID
    author_name: str | None = None
    author_email: EmailStr | None = None
    body: str
    is_staff_reply: bool
    created_at: datetime


class SupportTicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    user_email: EmailStr | None = None
    user_name: str | None = None
    subject: str
    status: SupportTicketStatus
    assigned_to_id: UUID | None
    assigned_to_name: str | None = None
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None
    messages_count: int = 0


class SupportTicketDetailResponse(SupportTicketResponse):
    messages: list[SupportMessageResponse] = Field(default_factory=list)
