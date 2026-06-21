import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.entities import (
    AppointmentStatus,
    CompanyService,
    MemberAppointment,
    SubscriptionPlan,
)
from app.repositories.tenant_repository import TenantRepository


def generate_invite_token() -> str:
    return secrets.token_urlsafe(32)


def build_activation_url(token: str) -> str:
    base = settings.invite_base_url.rstrip("/")
    return f"{base}/{token}"


def invite_token_expires_at() -> datetime:
    return datetime.now(UTC) + timedelta(days=settings.invite_token_expire_days)


async def count_company_services(db: AsyncSession, company_id) -> int:
    result = await db.scalar(
        select(func.count())
        .select_from(CompanyService)
        .where(
            CompanyService.company_id == company_id,
            CompanyService.is_active.is_(True),
        )
    )
    return result or 0


async def count_company_appointments_in_month(db: AsyncSession, company_id, *, at: datetime | None = None) -> int:
    now = at or datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        month_end = month_start.replace(year=now.year + 1, month=1)
    else:
        month_end = month_start.replace(month=now.month + 1)

    result = await db.scalar(
        select(func.count())
        .select_from(MemberAppointment)
        .where(
            MemberAppointment.company_id == company_id,
            MemberAppointment.starts_at >= month_start,
            MemberAppointment.starts_at < month_end,
            MemberAppointment.status.in_(
                [AppointmentStatus.SCHEDULED, AppointmentStatus.COMPLETED]
            ),
        )
    )
    return result or 0


async def get_plan_by_code(db: AsyncSession, code: str) -> SubscriptionPlan | None:
    result = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.code == code))
    return result.scalar_one_or_none()


async def grant_basic_subscription(db: AsyncSession, user_id) -> None:
    from app.models.entities import SubscriptionStatus, UserSubscription

    plan = await get_plan_by_code(db, "basic")
    if not plan:
        return

    existing = await db.execute(
        select(UserSubscription).where(
            UserSubscription.user_id == user_id,
            UserSubscription.plan_id == plan.id,
            UserSubscription.company_id.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        return

    db.add(
        UserSubscription(
            user_id=user_id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            expires_at=None,
        )
    )
    await db.flush()
