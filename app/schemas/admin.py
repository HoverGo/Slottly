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
    subscription_promotions_count: int = 0
    active_subscription_promotions_count: int = 0
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
    subscription_id: UUID | None = None
    plan_code: str | None = None
    plan_name: str | None = None
    subscription_status: str | None = None
    expires_at: datetime | None = None
    is_subscription_active: bool = False
    is_paid: bool = False
    is_free_plan: bool = False
    last_payment_status: str | None = None
    last_payment_paid_at: datetime | None = None
    last_payment_amount: int | None = None


class PlatformAnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1, max_length=10000)
    maintenance_starts_at: datetime | None = None
    maintenance_ends_at: datetime | None = None


class PlatformAnnouncementUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    message: str | None = Field(default=None, min_length=1, max_length=10000)
    maintenance_starts_at: datetime | None = None
    maintenance_ends_at: datetime | None = None
    is_active: bool | None = None
    clear_maintenance_starts_at: bool = False
    clear_maintenance_ends_at: bool = False


class PlatformAnnouncementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    message: str
    maintenance_starts_at: datetime | None
    maintenance_ends_at: datetime | None
    is_active: bool
    created_by_id: UUID
    created_by_name: str | None = None
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
    promotion_id: UUID | None = None
    promotion_name: str | None = None
    promotion_applied: bool = False


class SubscriptionPromotionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    discount_percent: int = Field(ge=1, le=100)
    plan_codes: list[str] | None = None
    actions: list[PaymentAction] | None = None
    for_all_companies: bool = True
    company_ids: list[UUID] | None = None
    first_plan_purchase_only: bool = False
    max_uses: int | None = Field(default=None, ge=1)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    description: str | None = Field(default=None, max_length=500)


class SubscriptionPromotionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    discount_percent: int | None = Field(default=None, ge=1, le=100)
    plan_codes: list[str] | None = None
    actions: list[PaymentAction] | None = None
    for_all_companies: bool | None = None
    company_ids: list[UUID] | None = None
    clear_company_ids: bool = False
    first_plan_purchase_only: bool | None = None
    max_uses: int | None = Field(default=None, ge=1)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    clear_valid_from: bool = False
    clear_valid_until: bool = False
    is_active: bool | None = None
    description: str | None = Field(default=None, max_length=500)


class SubscriptionPromotionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    discount_percent: int
    plan_codes: list[str] | None
    actions: list[str] | None
    for_all_companies: bool
    company_ids: list[str] | None
    first_plan_purchase_only: bool
    max_uses: int | None
    used_count: int
    valid_from: datetime | None
    valid_until: datetime | None
    is_active: bool
    description: str | None
    created_by_id: UUID
    created_at: datetime
