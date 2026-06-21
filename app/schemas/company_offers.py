from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CompanySubscriptionOfferUpsert(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)
    price_monthly: int = Field(ge=0, description="Индивидуальная цена за месяц, ниже базовой")
    max_users: int = Field(ge=1)
    max_branches: int = Field(ge=0)
    max_roles: int = Field(ge=1)
    max_services: int = Field(ge=0)
    max_appointments_per_month: int = Field(ge=0)
    base_plan_code: str | None = Field(default=None, max_length=50)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    is_active: bool = True
    description: str | None = Field(default=None, max_length=1000)


class CompanySubscriptionOfferUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)
    clear_display_name: bool = False
    price_monthly: int | None = Field(default=None, ge=0)
    max_users: int | None = Field(default=None, ge=1)
    max_branches: int | None = Field(default=None, ge=0)
    max_roles: int | None = Field(default=None, ge=1)
    max_services: int | None = Field(default=None, ge=0)
    max_appointments_per_month: int | None = Field(default=None, ge=0)
    base_plan_code: str | None = Field(default=None, max_length=50)
    clear_base_plan_code: bool = False
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    clear_valid_from: bool = False
    clear_valid_until: bool = False
    is_active: bool | None = None
    description: str | None = Field(default=None, max_length=1000)


class CompanySubscriptionOfferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    name: str
    display_name: str | None
    price_monthly: int
    max_users: int
    max_branches: int
    max_roles: int
    max_services: int
    max_appointments_per_month: int
    base_plan_code: str | None
    valid_from: datetime | None
    valid_until: datetime | None
    is_active: bool
    description: str | None
    created_by_id: UUID
    created_at: datetime
    updated_at: datetime
    company_name: str | None = None
