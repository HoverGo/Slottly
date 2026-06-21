import enum
import uuid
from datetime import date, datetime, time
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import PaymentAction, PaymentProvider


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class JoinRequestStatus(str, enum.Enum):
    PENDING = "pending"
    PENDING_ACTIVATION = "pending_activation"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class CompensationType(str, enum.Enum):
    PERCENT = "percent"
    SALARY = "salary"
    SALARY_PLUS_PERCENT = "salary_plus_percent"


class SchedulePatternType(str, enum.Enum):
    WEEKLY = "weekly"
    CYCLE = "cycle"
    MANUAL = "manual"


class ScheduleExceptionKind(str, enum.Enum):
    DAY_OFF = "day_off"
    SLOT_BLOCK = "slot_block"


class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class OrganizationType(str, enum.Enum):
    IP = "ip"
    SELF_EMPLOYED = "self_employed"
    LLC = "llc"


class WarehouseItemType(str, enum.Enum):
    PRODUCT = "product"
    CONSUMABLE = "consumable"


class StockMovementType(str, enum.Enum):
    RECEIPT = "receipt"
    ISSUE = "issue"
    ADJUSTMENT = "adjustment"
    TRANSFER = "transfer"


class SupportTicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_USER = "waiting_user"
    RESOLVED = "resolved"
    CLOSED = "closed"


class PlatformAnnouncement(Base):
    """Объявление платформы для всех компаний (техработы и т.п.)"""

    __tablename__ = "platform_announcements"
    __table_args__ = (Index("ix_platform_announcements_is_active", "is_active"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    maintenance_starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    maintenance_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_id])


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_platform_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_platform_support: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owned_companies: Mapped[list["Company"]] = relationship(back_populates="owner")
    memberships: Mapped[list["CompanyMember"]] = relationship(back_populates="user")
    subscriptions: Mapped[list["UserSubscription"]] = relationship(back_populates="user")
    payments: Mapped[list["Payment"]] = relationship(back_populates="user")
    join_requests: Mapped[list["CompanyJoinRequest"]] = relationship(
        back_populates="user", foreign_keys="CompanyJoinRequest.user_id"
    )
    support_tickets: Mapped[list["SupportTicket"]] = relationship(
        back_populates="user", foreign_keys="SupportTicket.user_id"
    )
    assigned_support_tickets: Mapped[list["SupportTicket"]] = relationship(
        back_populates="assigned_to", foreign_keys="SupportTicket.assigned_to_id"
    )


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_users: Mapped[int] = mapped_column(Integer, nullable=False)
    max_branches: Mapped[int] = mapped_column(Integer, nullable=False)
    max_roles: Mapped[int] = mapped_column(Integer, nullable=False)
    max_services: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    max_appointments_per_month: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    price_monthly: Mapped[int] = mapped_column(Integer, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    subscriptions: Mapped[list["UserSubscription"]] = relationship(
        back_populates="plan",
        foreign_keys="UserSubscription.plan_id",
    )


class UserSubscription(Base):
    """Подписка пользователя: одна активная подписка — одна компания"""

    __tablename__ = "user_subscriptions"
    __table_args__ = (
        Index("ix_user_subscriptions_user_id", "user_id"),
        Index("ix_user_subscriptions_company_id", "company_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=False
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True, unique=True
    )
    payment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=True)
    scheduled_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=True
    )
    scheduled_change_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status", create_type=False),
        default=SubscriptionStatus.ACTIVE,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="subscriptions")
    plan: Mapped["SubscriptionPlan"] = relationship(back_populates="subscriptions", foreign_keys=[plan_id])
    scheduled_plan: Mapped["SubscriptionPlan | None"] = relationship(foreign_keys=[scheduled_plan_id])
    company: Mapped["Company | None"] = relationship(
        back_populates="subscription", foreign_keys=[company_id]
    )
    payment: Mapped["Payment | None"] = relationship(foreign_keys=[payment_id])


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (Index("ix_payments_user_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=False
    )
    user_subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_subscriptions.id"), nullable=True
    )
    action: Mapped[PaymentAction] = mapped_column(Enum(PaymentAction, name="payment_action"), nullable=False)
    period_months: Mapped[int] = mapped_column(Integer, nullable=False)
    provider: Mapped[PaymentProvider] = mapped_column(
        Enum(PaymentProvider, name="payment_provider"), nullable=False
    )
    provider_payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    original_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discount_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="RUB", nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status"), default=PaymentStatus.PENDING, nullable=False
    )
    confirmation_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    promo_code_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("promo_codes.id"), nullable=True
    )
    provider_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="payments")
    plan: Mapped["SubscriptionPlan"] = relationship()
    user_subscription: Mapped["UserSubscription | None"] = relationship(
        foreign_keys=[user_subscription_id],
    )
    promo_code: Mapped["PromoCode | None"] = relationship(foreign_keys=[promo_code_id])


class PromoCode(Base):
    """Промокод на скидку при оплате подписки"""

    __tablename__ = "promo_codes"
    __table_args__ = (Index("ix_promo_codes_user_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    discount_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    plan_codes: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    actions: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User | None"] = relationship(foreign_keys=[user_id])
    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_id])


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    photo_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    organization_type: Mapped[OrganizationType | None] = mapped_column(
        Enum(OrganizationType, name="organization_type"), nullable=True
    )
    working_hours: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    booking_slug: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    public_booking_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_owner_first_company: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped["User"] = relationship(back_populates="owned_companies")
    subscription: Mapped["UserSubscription | None"] = relationship(
        back_populates="company",
        foreign_keys="UserSubscription.company_id",
        uselist=False,
    )
    roles: Mapped[list["CompanyRole"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    members: Mapped[list["CompanyMember"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    branches: Mapped[list["Branch"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    join_requests: Mapped[list["CompanyJoinRequest"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    services: Mapped[list["CompanyService"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    clients: Mapped[list["CompanyClient"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    gallery_photos: Mapped[list["CompanyGalleryPhoto"]] = relationship(
        back_populates="company", cascade="all, delete-orphan", order_by="CompanyGalleryPhoto.sort_order"
    )
    requisites: Mapped["CompanyRequisites | None"] = relationship(
        back_populates="company", cascade="all, delete-orphan", uselist=False
    )
    warehouse_items: Mapped[list["WarehouseItem"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["CompanyReview"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )


class CompanyRequisites(Base):
    """Реквизиты организации для выставления счетов"""

    __tablename__ = "company_requisites"
    __table_args__ = (
        UniqueConstraint("company_id", name="uq_company_requisites_company_id"),
        Index("ix_company_requisites_company_id", "company_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    inn: Mapped[str] = mapped_column(String(12), nullable=False)
    kpp: Mapped[str | None] = mapped_column(String(9), nullable=True)
    billing_email: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    company: Mapped["Company"] = relationship(back_populates="requisites")


class CompanyGalleryPhoto(Base):
    """Фото студии компании"""

    __tablename__ = "company_gallery_photos"
    __table_args__ = (Index("ix_company_gallery_photos_company_id", "company_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="gallery_photos")


class CompanyRole(Base):
    __tablename__ = "company_roles"
    __table_args__ = (
        UniqueConstraint("company_id", "id", name="uq_company_role_tenant"),
        UniqueConstraint("company_id", "name", name="uq_company_role_name"),
        Index("ix_company_roles_company_id", "company_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    permissions: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="roles")
    members: Mapped[list["CompanyMember"]] = relationship(back_populates="role")


class CompanyMember(Base):
    __tablename__ = "company_members"
    __table_args__ = (
        UniqueConstraint("company_id", "user_id", name="uq_company_member"),
        ForeignKeyConstraint(
            ["company_id", "role_id"],
            ["company_roles.company_id", "company_roles.id"],
            name="fk_member_role_same_tenant",
        ),
        Index("ix_company_members_company_id", "company_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    photo_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    compensation_type: Mapped[CompensationType | None] = mapped_column(
        Enum(CompensationType, name="compensation_type"), nullable=True
    )
    compensation_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    compensation_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="memberships")
    role: Mapped["CompanyRole"] = relationship(back_populates="members")
    work_schedules: Mapped[list["MemberWorkSchedule"]] = relationship(
        back_populates="member", cascade="all, delete-orphan"
    )
    schedule_exceptions: Mapped[list["MemberScheduleException"]] = relationship(
        back_populates="member", cascade="all, delete-orphan"
    )
    appointments: Mapped[list["MemberAppointment"]] = relationship(
        back_populates="member", cascade="all, delete-orphan"
    )


class MemberWorkSchedule(Base):
    __tablename__ = "member_work_schedules"
    __table_args__ = (
        Index("ix_member_work_schedules_company_id", "company_id"),
        Index("ix_member_work_schedules_member_id", "member_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("company_members.id"), nullable=False
    )
    date_from: Mapped[date] = mapped_column(nullable=False)
    date_to: Mapped[date] = mapped_column(nullable=False)
    time_start: Mapped[time] = mapped_column(Time, nullable=False)
    time_end: Mapped[time] = mapped_column(Time, nullable=False)
    slot_interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    pattern_type: Mapped[SchedulePatternType] = mapped_column(
        Enum(SchedulePatternType, name="schedule_pattern_type"), nullable=False
    )
    pattern_config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    member: Mapped["CompanyMember"] = relationship(back_populates="work_schedules")
    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_id])


class MemberScheduleException(Base):
    """Исключения расписания: выходной день или блокировка отдельных слотов"""

    __tablename__ = "member_schedule_exceptions"
    __table_args__ = (
        Index("ix_member_schedule_exceptions_company_id", "company_id"),
        Index("ix_member_schedule_exceptions_member_id", "member_id"),
        Index("ix_member_schedule_exceptions_date", "exception_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("company_members.id"), nullable=False
    )
    exception_date: Mapped[date] = mapped_column(nullable=False)
    exception_date_to: Mapped[date | None] = mapped_column(nullable=True)
    exception_dates: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    kind: Mapped[ScheduleExceptionKind] = mapped_column(
        Enum(ScheduleExceptionKind, name="schedule_exception_kind"), nullable=False
    )
    block_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    member: Mapped["CompanyMember"] = relationship(back_populates="schedule_exceptions")
    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_id])


class SupportTicket(Base):
    __tablename__ = "support_tickets"
    __table_args__ = (
        Index("ix_support_tickets_user_id", "user_id"),
        Index("ix_support_tickets_status", "status"),
        Index("ix_support_tickets_assigned_to_id", "assigned_to_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[SupportTicketStatus] = mapped_column(
        Enum(SupportTicketStatus, name="support_ticket_status"), nullable=False
    )
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="support_tickets", foreign_keys=[user_id])
    assigned_to: Mapped["User | None"] = relationship(
        back_populates="assigned_support_tickets", foreign_keys=[assigned_to_id]
    )
    messages: Mapped[list["SupportTicketMessage"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan", order_by="SupportTicketMessage.created_at"
    )


class SupportTicketMessage(Base):
    __tablename__ = "support_ticket_messages"
    __table_args__ = (Index("ix_support_ticket_messages_ticket_id", "ticket_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_staff_reply: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ticket: Mapped["SupportTicket"] = relationship(back_populates="messages")
    author: Mapped["User"] = relationship(foreign_keys=[author_id])


class CompanyJoinRequest(Base):
    __tablename__ = "company_join_requests"
    __table_args__ = (
        Index("ix_join_requests_user_id", "user_id"),
        Index("ix_join_requests_company_id", "company_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    invite_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    invite_full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    invite_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    activation_token: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    invited_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    compensation_type: Mapped[CompensationType | None] = mapped_column(
        Enum(CompensationType, name="compensation_type", create_type=False), nullable=True
    )
    compensation_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    compensation_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[JoinRequestStatus] = mapped_column(
        Enum(JoinRequestStatus, name="join_request_status", create_type=False),
        default=JoinRequestStatus.PENDING,
        nullable=False,
    )
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    company: Mapped["Company"] = relationship(back_populates="join_requests")
    user: Mapped["User"] = relationship(back_populates="join_requests", foreign_keys=[user_id])
    invited_by: Mapped["User"] = relationship(foreign_keys=[invited_by_id])
    role: Mapped["CompanyRole"] = relationship(
        foreign_keys=[role_id],
        primaryjoin="CompanyJoinRequest.role_id == CompanyRole.id",
    )


class Branch(Base):
    __tablename__ = "branches"
    __table_args__ = (
        UniqueConstraint("company_id", "id", name="uq_branch_tenant"),
        Index("ix_branches_company_id", "company_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="branches")
    services: Mapped[list["CompanyService"]] = relationship(back_populates="branch")


class CompanyService(Base):
    """Услуга компании с длительностью для записи клиентов"""

    __tablename__ = "company_services"
    __table_args__ = (
        UniqueConstraint("company_id", "id", name="uq_company_service_tenant"),
        Index("ix_company_services_company_id", "company_id"),
        Index("ix_company_services_member_id", "member_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    buffer_before_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    buffer_after_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    member_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("company_members.id"), nullable=True
    )
    branch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("branches.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="services")
    member: Mapped["CompanyMember | None"] = relationship(foreign_keys=[member_id])
    branch: Mapped["Branch | None"] = relationship(
        back_populates="services",
        foreign_keys=[branch_id],
        primaryjoin="CompanyService.branch_id == Branch.id",
    )
    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_id])
    appointments: Mapped[list["MemberAppointment"]] = relationship(back_populates="service")


class MemberAppointment(Base):
    """Запись клиента на услугу у специалиста"""

    __tablename__ = "member_appointments"
    __table_args__ = (
        Index("ix_member_appointments_company_id", "company_id"),
        Index("ix_member_appointments_member_id", "member_id"),
        Index("ix_member_appointments_starts_at", "starts_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("company_members.id"), nullable=False
    )
    service_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company_services.id"), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    buffer_before_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    buffer_after_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("company_clients.id"), nullable=True
    )
    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    client_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus, name="appointment_status"), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    member: Mapped["CompanyMember"] = relationship(back_populates="appointments")
    service: Mapped["CompanyService"] = relationship(back_populates="appointments")
    client: Mapped["CompanyClient | None"] = relationship(back_populates="appointments")
    created_by: Mapped["User | None"] = relationship(foreign_keys=[created_by_id])


class CompanyClient(Base):
    """Клиент компании, идентифицируется по номеру телефона в рамках компании"""

    __tablename__ = "company_clients"
    __table_args__ = (
        UniqueConstraint("company_id", "phone_normalized", name="uq_company_client_phone"),
        Index("ix_company_clients_company_id", "company_id"),
        Index("ix_company_clients_phone_normalized", "phone_normalized"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    phone_normalized: Mapped[str] = mapped_column(String(20), nullable=False)
    phone_display: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    company: Mapped["Company"] = relationship(back_populates="clients")
    appointments: Mapped[list["MemberAppointment"]] = relationship(back_populates="client")
    reviews: Mapped[list["CompanyReview"]] = relationship(back_populates="client")


class WarehouseItem(Base):
    """Товар или расходник на складе компании"""

    __tablename__ = "warehouse_items"
    __table_args__ = (
        UniqueConstraint("company_id", "id", name="uq_warehouse_item_tenant"),
        UniqueConstraint("company_id", "sku", name="uq_warehouse_item_sku"),
        Index("ix_warehouse_items_company_id", "company_id"),
        Index("ix_warehouse_items_item_type", "item_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    item_type: Mapped[WarehouseItemType] = mapped_column(
        Enum(WarehouseItemType, name="warehouse_item_type"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(64), nullable=True)
    unit: Mapped[str] = mapped_column(String(20), default="шт", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    min_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    company: Mapped["Company"] = relationship(back_populates="warehouse_items")
    stock_balances: Mapped[list["WarehouseStock"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )
    movements: Mapped[list["WarehouseMovement"]] = relationship(back_populates="item")
    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_id])


class WarehouseStock(Base):
    """Остаток позиции на складе (основной или филиал)"""

    __tablename__ = "warehouse_stock"
    __table_args__ = (
        UniqueConstraint("company_id", "item_id", "branch_id", name="uq_warehouse_stock_location"),
        Index("ix_warehouse_stock_company_id", "company_id"),
        Index("ix_warehouse_stock_item_id", "item_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouse_items.id"), nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("branches.id"), nullable=True
    )
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    item: Mapped["WarehouseItem"] = relationship(back_populates="stock_balances")
    branch: Mapped["Branch | None"] = relationship(foreign_keys=[branch_id])


class WarehouseMovement(Base):
    """Движение по складу: приход, расход, корректировка, перемещение"""

    __tablename__ = "warehouse_movements"
    __table_args__ = (
        Index("ix_warehouse_movements_company_id", "company_id"),
        Index("ix_warehouse_movements_item_id", "item_id"),
        Index("ix_warehouse_movements_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouse_items.id"), nullable=False)
    movement_type: Mapped[StockMovementType] = mapped_column(
        Enum(StockMovementType, name="stock_movement_type"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("branches.id"), nullable=True
    )
    from_branch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("branches.id"), nullable=True
    )
    to_branch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("branches.id"), nullable=True
    )
    quantity_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quantity_after: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    item: Mapped["WarehouseItem"] = relationship(back_populates="movements")
    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_id])


class CompanyReview(Base):
    """Отзыв клиента о компании с опциональной привязкой к мастеру"""

    __tablename__ = "company_reviews"
    __table_args__ = (
        Index("ix_company_reviews_company_id", "company_id"),
        Index("ix_company_reviews_member_id", "member_id"),
        Index("ix_company_reviews_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("company_clients.id"), nullable=False
    )
    member_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("company_members.id"), nullable=True
    )
    client_display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="reviews")
    client: Mapped["CompanyClient"] = relationship(back_populates="reviews")
    member: Mapped["CompanyMember | None"] = relationship(foreign_keys=[member_id])
