from datetime import datetime
import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def passwords_must_differ(self) -> "PasswordChange":
        if self.current_password == self.new_password:
            raise ValueError("Новый пароль должен отличаться от текущего")
        return self


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    is_active: bool
    is_platform_admin: bool = False
    is_platform_support: bool = False
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    subscription_id: UUID


class CompanyDayHours(BaseModel):
    is_closed: bool = False
    open: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    close: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")

    @model_validator(mode="after")
    def validate_times(self) -> "CompanyDayHours":
        if self.is_closed:
            return self
        if not self.open or not self.close:
            raise ValueError("Укажите open и close или is_closed=true")
        if self.open >= self.close:
            raise ValueError("close должно быть позже open")
        return self


class CompanyWorkingHours(BaseModel):
    monday: CompanyDayHours | None = None
    tuesday: CompanyDayHours | None = None
    wednesday: CompanyDayHours | None = None
    thursday: CompanyDayHours | None = None
    friday: CompanyDayHours | None = None
    saturday: CompanyDayHours | None = None
    sunday: CompanyDayHours | None = None


OrganizationTypeLiteral = Literal["ip", "self_employed", "llc"]


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    country: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=50)
    organization_type: OrganizationTypeLiteral | None = None
    working_hours: CompanyWorkingHours | None = None
    booking_slug: str | None = Field(default=None, max_length=64)
    public_booking_enabled: bool | None = None
    clear_country: bool = False
    clear_city: bool = False
    clear_address: bool = False
    clear_phone: bool = False
    clear_organization_type: bool = False
    clear_working_hours: bool = False


class CompanyGalleryPhotoResponse(BaseModel):
    id: UUID
    url: str
    sort_order: int
    created_at: datetime


class CompanyRequisitesUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255, description="Название организации")
    inn: str = Field(min_length=10, max_length=12, description="ИНН")
    kpp: str | None = Field(default=None, min_length=9, max_length=9, description="КПП")
    billing_email: EmailStr = Field(description="Email для счетов")

    @model_validator(mode="after")
    def validate_requisites(self) -> "CompanyRequisitesUpdate":
        inn_digits = re.sub(r"\D", "", self.inn)
        if len(inn_digits) not in (10, 12):
            raise ValueError("ИНН должен содержать 10 или 12 цифр")
        object.__setattr__(self, "inn", inn_digits)

        if self.kpp is not None:
            kpp_digits = re.sub(r"\D", "", self.kpp)
            if len(kpp_digits) != 9:
                raise ValueError("КПП должен содержать 9 цифр")
            object.__setattr__(self, "kpp", kpp_digits)
        return self


class CompanyRequisitesResponse(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    inn: str
    kpp: str | None
    billing_email: EmailStr
    created_at: datetime
    updated_at: datetime | None = None


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    owner_id: UUID
    country: str | None = None
    city: str | None = None
    address: str | None = None
    phone: str | None = None
    organization_type: OrganizationTypeLiteral | None = None
    working_hours: CompanyWorkingHours | None = None
    logo_url: str | None = None
    photo_url: str | None = None
    gallery: list[CompanyGalleryPhotoResponse] = Field(default_factory=list)
    booking_slug: str | None = None
    public_booking_enabled: bool = False
    booking_url: str | None = None
    rating_average: float = 0.0
    rating_count: int = 0
    is_owner_first_company: bool
    created_at: datetime
    updated_at: datetime | None = None
    has_active_subscription: bool = False
    is_owner: bool = False


class CompanyRoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    permissions: list[str] = Field(default_factory=list)


class CompanyRoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    permissions: list[str] | None = None


class CompanyRoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    name: str
    description: str | None
    permissions: list[str]
    created_at: datetime


class CompanyMemberUpdate(BaseModel):
    role_id: UUID | None = None
    compensation_type: Literal["percent", "salary", "salary_plus_percent"] | None = None
    compensation_rate: int | None = Field(default=None, ge=0)
    compensation_percent: int | None = Field(default=None, ge=1, le=100)
    clear_compensation: bool = False


class CompanyMemberCreate(BaseModel):
    user_id: UUID
    role_id: UUID


class CompanyMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    user_id: UUID
    role_id: UUID
    compensation_type: Literal["percent", "salary", "salary_plus_percent"] | None = None
    compensation_rate: int | None = None
    compensation_percent: int | None = None
    photo_url: str | None = None
    created_at: datetime


class BranchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address: str | None = Field(default=None, max_length=500)


class BranchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    name: str
    address: str | None
    created_at: datetime


class SubscriptionPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None
    max_users: int
    max_branches: int
    max_roles: int
    max_services: int
    max_appointments_per_month: int
    price_monthly: int


class SubscriptionLimitsResponse(BaseModel):
    max_users: int
    max_branches: int
    max_roles: int
    max_services: int
    max_appointments_per_month: int
    current_users: int
    current_branches: int
    current_roles: int
    current_services: int
    current_appointments_this_month: int
    has_active_subscription: bool
    expires_at: datetime | None = None
    scheduled_plan_code: str | None = None
    scheduled_change_at: datetime | None = None
