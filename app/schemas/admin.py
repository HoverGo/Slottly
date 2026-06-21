from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

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
    is_platform_main_admin: bool
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


class PlatformMainAdminUpdate(BaseModel):
    is_platform_main_admin: bool


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    actor_user_id: UUID | None
    actor_email: str | None
    action: str
    category: str
    resource_type: str | None
    resource_id: UUID | None
    company_id: UUID | None
    ip_address: str | None
    user_agent: str | None
    method: str | None
    path: str | None
    status_code: int | None
    success: bool
    details: dict | None


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int


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
    custom_offer_applied: bool = False
    custom_offer_name: str | None = None


class PromotionCompanyRef(BaseModel):
    id: UUID
    name: str


class SubscriptionPromotionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    plan_code: str = Field(min_length=1, max_length=50)
    period_months: Literal[1, 3, 6, 12]
    promotional_amount: int = Field(ge=1, description="Итоговая стоимость за период, ниже базовой")
    for_all_companies: bool = True
    company_ids: list[UUID] | None = Field(
        default=None,
        description="UUID компаний, если for_all_companies=false. Список id из GET /admin/companies",
    )
    new_companies_only: bool = False
    is_active: bool = True
    max_uses: int | None = Field(default=None, ge=1)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    description: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_company_scope(self) -> "SubscriptionPromotionCreate":
        if self.for_all_companies:
            return self
        if not self.company_ids:
            raise ValueError("Укажите company_ids — id компаний, для которых действует акция")
        if len(self.company_ids) != len(set(self.company_ids)):
            raise ValueError("company_ids не должны содержать дубликаты")
        return self


class SubscriptionPromotionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    plan_code: str | None = Field(default=None, min_length=1, max_length=50)
    period_months: Literal[1, 3, 6, 12] | None = None
    promotional_amount: int | None = Field(default=None, ge=1)
    for_all_companies: bool | None = None
    company_ids: list[UUID] | None = Field(
        default=None,
        description="UUID компаний, если акция не для всех",
    )
    clear_company_ids: bool = False
    new_companies_only: bool | None = None
    max_uses: int | None = Field(default=None, ge=1)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    clear_valid_from: bool = False
    clear_valid_until: bool = False
    is_active: bool | None = None
    description: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_company_scope(self) -> "SubscriptionPromotionUpdate":
        if self.company_ids and len(self.company_ids) != len(set(self.company_ids)):
            raise ValueError("company_ids не должны содержать дубликаты")
        if self.for_all_companies is False and not self.company_ids and not self.clear_company_ids:
            raise ValueError(
                "При for_all_companies=false укажите company_ids — id выбранных компаний"
            )
        return self


class SubscriptionPromotionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    plan_code: str
    period_months: int
    promotional_amount: int
    for_all_companies: bool
    company_ids: list[str] | None
    companies: list[PromotionCompanyRef] = Field(
        default_factory=list,
        description="Выбранные компании (id и название), если акция не для всех",
    )
    new_companies_only: bool
    max_uses: int | None
    used_count: int
    valid_from: datetime | None
    valid_until: datetime | None
    is_active: bool
    description: str | None
    created_by_id: UUID
    created_at: datetime
