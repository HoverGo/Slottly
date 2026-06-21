from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.entities import CompensationType, JoinRequestStatus, PaymentStatus
from app.models.enums import PaymentAction
from app.schemas.schemas import CompanyResponse, SubscriptionPlanResponse, UserResponse


class PaymentCheckoutCreate(BaseModel):
    plan_code: str = Field(min_length=1, max_length=50)
    action: PaymentAction
    period_months: Literal[1, 3, 6, 12]
    subscription_id: UUID | None = None
    promo_code: str | None = Field(default=None, min_length=3, max_length=50)


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plan_id: UUID
    user_subscription_id: UUID | None
    action: PaymentAction
    period_months: int
    provider: str
    original_amount: int | None = None
    discount_amount: int = 0
    amount: int
    currency: str
    status: PaymentStatus
    promo_code: str | None = None
    confirmation_url: str | None
    created_at: datetime
    paid_at: datetime | None
    plan: SubscriptionPlanResponse


class UserSubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plan_id: UUID
    company_id: UUID | None
    status: str
    started_at: datetime
    expires_at: datetime | None
    scheduled_plan_id: UUID | None = None
    scheduled_change_at: datetime | None = None
    plan: SubscriptionPlanResponse
    scheduled_plan: SubscriptionPlanResponse | None = None
    is_available_for_company: bool = False


class JoinRequestCreate(BaseModel):
    email: EmailStr
    role_id: UUID
    message: str | None = Field(default=None, max_length=1000)
    full_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    compensation_type: Literal["percent", "salary", "salary_plus_percent"] | None = None
    compensation_rate: int | None = Field(default=None, ge=0)
    compensation_percent: int | None = Field(default=None, ge=1, le=100)


class JoinRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    user_id: UUID | None
    role_id: UUID
    invited_by_id: UUID
    status: JoinRequestStatus
    message: str | None
    created_at: datetime
    responded_at: datetime | None
    company_name: str | None = None
    role_name: str | None = None
    invited_by_name: str | None = None
    invite_email: str | None = None
    invite_full_name: str | None = None
    invite_phone: str | None = None
    activation_url: str | None = None
    compensation_type: Literal["percent", "salary", "salary_plus_percent"] | None = None
    compensation_rate: int | None = None
    compensation_percent: int | None = None


class InvitePreviewResponse(BaseModel):
    company_name: str
    role_name: str
    invite_email: str
    invite_full_name: str | None
    invite_phone: str | None
    invited_by_name: str | None
    message: str | None
    compensation_type: Literal["percent", "salary", "salary_plus_percent"] | None = None
    compensation_rate: int | None = None
    compensation_percent: int | None = None
    token_expires_at: datetime | None


class InviteActivateRequest(BaseModel):
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class InviteActivateResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    member_id: UUID
    company_id: UUID


class PlatformAnnouncementPublicResponse(BaseModel):
    id: UUID
    title: str
    message: str
    maintenance_starts_at: datetime | None
    maintenance_ends_at: datetime | None
    created_at: datetime


class CabinetResponse(BaseModel):
    user: UserResponse
    can_create_company: bool
    subscriptions: list[UserSubscriptionResponse]
    available_subscription_slots: int
    companies: list[CompanyResponse]
    pending_join_requests: list[JoinRequestResponse]
    platform_announcements: list[PlatformAnnouncementPublicResponse] = Field(default_factory=list)
