from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import PaymentAction
from app.schemas.schemas import SubscriptionPlanResponse, UserResponse


class AdminDashboardResponse(BaseModel):
    users_count: int
    companies_count: int
    successful_payments_count: int
    subscriptions_count: int
    promo_codes_count: int
    active_promo_codes_count: int
    open_support_tickets_count: int = 0


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    is_active: bool
    is_platform_admin: bool
    is_platform_support: bool
    created_at: datetime


class AdminCompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    owner_id: UUID
    owner_email: EmailStr | None = None
    owner_name: str | None = None
    is_owner_first_company: bool
    created_at: datetime


class PromoCodeCreate(BaseModel):
    code: str = Field(min_length=3, max_length=50)
    discount_percent: int = Field(ge=1, le=100)
    user_id: UUID | None = None
    user_email: EmailStr | None = None
    plan_codes: list[str] | None = None
    actions: list[PaymentAction] | None = None
    max_uses: int | None = Field(default=None, ge=1)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    description: str | None = Field(default=None, max_length=500)


class PromoCodeUpdate(BaseModel):
    discount_percent: int | None = Field(default=None, ge=1, le=100)
    plan_codes: list[str] | None = None
    actions: list[PaymentAction] | None = None
    max_uses: int | None = Field(default=None, ge=1)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    clear_valid_from: bool = False
    clear_valid_until: bool = False
    is_active: bool | None = None
    description: str | None = Field(default=None, max_length=500)


class PromoCodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    discount_percent: int
    user_id: UUID | None
    user_email: EmailStr | None = None
    user_name: str | None = None
    plan_codes: list[str] | None
    actions: list[str] | None
    max_uses: int | None
    used_count: int
    valid_from: datetime | None
    valid_until: datetime | None
    is_active: bool
    description: str | None
    created_by_id: UUID
    created_at: datetime


class PlatformAdminUpdate(BaseModel):
    is_platform_admin: bool


class PlatformSupportUpdate(BaseModel):
    is_platform_support: bool


class PaymentCheckoutPreviewRequest(BaseModel):
    plan_code: str = Field(min_length=1, max_length=50)
    action: PaymentAction
    period_months: Literal[1, 3, 6, 12]
    subscription_id: UUID | None = None
    promo_code: str | None = Field(default=None, min_length=3, max_length=50)


class PaymentCheckoutPreviewResponse(BaseModel):
    plan: SubscriptionPlanResponse
    action: PaymentAction
    period_months: int
    original_amount: int
    discount_amount: int
    amount: int
    currency: str = "RUB"
    promo_code: str | None = None
    promo_applied: bool
    promo_error: str | None = None
