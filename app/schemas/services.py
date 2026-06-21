from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CompanyServiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    duration_minutes: int = Field(ge=5, le=480)
    price: int | None = Field(default=None, ge=0)
    member_id: UUID | None = None
    branch_id: UUID | None = None


class CompanyServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    duration_minutes: int | None = Field(default=None, ge=5, le=480)
    price: int | None = None
    member_id: UUID | None = None
    branch_id: UUID | None = None
    is_active: bool | None = None
    clear_member: bool = False
    clear_branch: bool = False


class CompanyServiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    name: str
    description: str | None
    duration_minutes: int
    price: int | None
    member_id: UUID | None
    branch_id: UUID | None
    is_active: bool
    created_by_id: UUID
    created_at: Any


class AppointmentCreate(BaseModel):
    service_id: UUID
    starts_at: datetime
    client_name: str | None = Field(default=None, max_length=255)
    client_phone: str | None = Field(default=None, max_length=50)
    note: str | None = Field(default=None, max_length=500)


class AppointmentUpdate(BaseModel):
    status: Literal["scheduled", "cancelled", "completed"] | None = None
    client_name: str | None = Field(default=None, max_length=255)
    client_phone: str | None = Field(default=None, max_length=50)
    note: str | None = Field(default=None, max_length=500)


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
    client_name: str | None
    client_phone: str | None
    status: Literal["scheduled", "cancelled", "completed"]
    note: str | None
    created_by_id: UUID
    created_at: Any
