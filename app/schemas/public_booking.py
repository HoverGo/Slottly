from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.schemas.schemas import CompanyWorkingHours
from app.schemas.services import ServiceBufferMinutes


class PublicBookingCompanyResponse(BaseModel):
    slug: str
    name: str
    city: str | None = None
    address: str | None = None
    phone: str | None = None
    working_hours: CompanyWorkingHours | None = None
    logo_url: str | None = None
    gallery: list[dict[str, Any]] = Field(default_factory=list)
    rating_average: float = 0.0
    rating_count: int = 0


class PublicBookingMemberResponse(BaseModel):
    id: UUID
    full_name: str
    role_name: str | None = None
    photo_url: str | None = None


class PublicBookingServiceResponse(BaseModel):
    id: UUID
    name: str
    category: str | None = None
    description: str | None = None
    duration_minutes: int
    buffer_before_minutes: ServiceBufferMinutes
    buffer_after_minutes: ServiceBufferMinutes
    price: int | None = None
    member_id: UUID | None = None


class PublicBookingSlotsResponse(BaseModel):
    member_id: UUID
    service_id: UUID
    from_date: date
    to_date: date
    slots_by_day: dict[str, list[str]]


class PublicAppointmentCreate(BaseModel):
    service_id: UUID
    starts_at: datetime
    client_name: str | None = Field(default=None, max_length=255)
    client_full_name: str | None = Field(default=None, max_length=255)
    client_phone: str = Field(min_length=5, max_length=50)
    client_email: EmailStr | None = None
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_name_or_full_name(self) -> "PublicAppointmentCreate":
        if not (self.client_name and self.client_name.strip()) and not (
            self.client_full_name and self.client_full_name.strip()
        ):
            raise ValueError("Укажите client_name или client_full_name")
        return self


class PublicAppointmentResponse(BaseModel):
    id: UUID
    member_id: UUID
    member_name: str | None = None
    service_id: UUID
    service_name: str | None = None
    starts_at: datetime
    ends_at: datetime
    duration_minutes: int
    status: Literal["scheduled", "cancelled", "completed"]
