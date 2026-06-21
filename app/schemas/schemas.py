from datetime import datetime
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


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    owner_id: UUID
    is_owner_first_company: bool
    created_at: datetime
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
    role_id: UUID


class CompanyMemberCreate(BaseModel):
    user_id: UUID
    role_id: UUID


class CompanyMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    user_id: UUID
    role_id: UUID
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
    price_monthly: int


class SubscriptionLimitsResponse(BaseModel):
    max_users: int
    max_branches: int
    max_roles: int
    current_users: int
    current_branches: int
    current_roles: int
    has_active_subscription: bool
    expires_at: datetime | None = None
    scheduled_plan_code: str | None = None
    scheduled_change_at: datetime | None = None
