from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

ServiceBufferMinutes = Literal[0, 5, 10, 15, 30]


class CompanyServiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=100, description="Категория услуги")
    description: str | None = Field(default=None, max_length=2000)
    duration_minutes: int = Field(ge=5, le=480)
    buffer_before_minutes: ServiceBufferMinutes = Field(default=0, description="Буфер до услуги")
    buffer_after_minutes: ServiceBufferMinutes = Field(default=0, description="Буфер после услуги")
    price: int | None = Field(default=None, ge=0)
    member_id: UUID | None = Field(default=None, description="Исполнитель из сотрудников компании")
    branch_id: UUID | None = None


class CompanyServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    duration_minutes: int | None = Field(default=None, ge=5, le=480)
    buffer_before_minutes: ServiceBufferMinutes | None = None
    buffer_after_minutes: ServiceBufferMinutes | None = None
    price: int | None = None
    member_id: UUID | None = None
    branch_id: UUID | None = None
    is_active: bool | None = None
    clear_member: bool = False
    clear_branch: bool = False
    clear_category: bool = False


class CompanyServiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    name: str
    category: str | None
    description: str | None
    duration_minutes: int
    buffer_before_minutes: ServiceBufferMinutes
    buffer_after_minutes: ServiceBufferMinutes
    price: int | None
    member_id: UUID | None
    member_name: str | None = None
    branch_id: UUID | None
    is_active: bool
    created_by_id: UUID
    created_at: Any


class AppointmentCreate(BaseModel):
    service_id: UUID
    starts_at: datetime
    client_name: str | None = Field(default=None, max_length=255, description="Имя")
    client_full_name: str | None = Field(default=None, max_length=255, description="ФИО")
    client_phone: str = Field(min_length=5, max_length=50)
    client_email: EmailStr | None = None
    note: str | None = Field(default=None, max_length=2000, description="Дополнительная информация")

    @model_validator(mode="after")
    def require_name_or_full_name(self) -> "AppointmentCreate":
        if not (self.client_name and self.client_name.strip()) and not (
            self.client_full_name and self.client_full_name.strip()
        ):
            raise ValueError("Укажите client_name или client_full_name")
        return self


class AppointmentUpdate(BaseModel):
    status: Literal["scheduled", "cancelled", "completed"] | None = None
    client_name: str | None = Field(default=None, max_length=255)
    client_full_name: str | None = Field(default=None, max_length=255)
    client_phone: str | None = Field(default=None, min_length=5, max_length=50)
    client_email: EmailStr | None = None
    note: str | None = Field(default=None, max_length=2000)


class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    member_id: UUID
    service_id: UUID
    service_name: str | None = None
    starts_at: datetime
    duration_minutes: int
    ends_at: datetime
    client_id: UUID | None = None
    client_name: str | None
    client_full_name: str | None = None
    client_phone: str | None
    client_email: EmailStr | None = None
    status: Literal["scheduled", "cancelled", "completed"]
    note: str | None
    member_name: str | None = None
    created_by_id: UUID | None
    created_at: Any


class CompanyClientResponse(BaseModel):
    id: UUID
    company_id: UUID
    phone: str
    phone_normalized: str
    name: str | None
    full_name: str | None
    email: EmailStr | None
    appointments_count: int | None = None
    created_at: Any
    updated_at: Any


class ClientAppointmentHistoryItem(BaseModel):
    id: UUID
    service_id: UUID
    service_name: str | None
    member_id: UUID
    member_name: str | None
    branch_id: UUID | None
    branch_name: str | None
    starts_at: datetime
    ends_at: datetime
    duration_minutes: int
    status: Literal["scheduled", "cancelled", "completed"]
    client_name: str | None
    client_full_name: str | None
    client_phone: str | None
    client_email: EmailStr | None
    note: str | None
    created_at: Any


class ClientHistoryResponse(BaseModel):
    client: CompanyClientResponse
    appointments: list[ClientAppointmentHistoryItem]
