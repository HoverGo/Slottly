from datetime import date, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entities import (
    AppointmentStatus,
    Branch,
    CompanyMember,
    CompanyRole,
    CompanyService,
    MemberAppointment,
    MemberScheduleException,
    MemberWorkSchedule,
    ScheduleExceptionKind,
    SubscriptionStatus,
    UserSubscription,
)


class TenantRepository:
    """Все запросы к данным компании — только в рамках company_id"""

    def __init__(self, db: AsyncSession, company_id):
        self.db = db
        self.company_id = company_id

    async def list_roles(self) -> list[CompanyRole]:
        result = await self.db.execute(
            select(CompanyRole)
            .where(CompanyRole.company_id == self.company_id)
            .order_by(CompanyRole.created_at)
        )
        return list(result.scalars().all())

    async def get_role_by_id(self, role_id):
        result = await self.db.execute(
            select(CompanyRole).where(
                CompanyRole.id == role_id,
                CompanyRole.company_id == self.company_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_role_by_name(self, name: str) -> CompanyRole | None:
        result = await self.db.execute(
            select(CompanyRole).where(
                CompanyRole.company_id == self.company_id,
                CompanyRole.name == name,
            )
        )
        return result.scalar_one_or_none()

    async def list_members(self) -> list[CompanyMember]:
        result = await self.db.execute(
            select(CompanyMember)
            .where(CompanyMember.company_id == self.company_id)
            .order_by(CompanyMember.created_at)
        )
        return list(result.scalars().all())

    async def get_member_by_user_id(self, user_id):
        result = await self.db.execute(
            select(CompanyMember).where(
                CompanyMember.company_id == self.company_id,
                CompanyMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_branches(self) -> list[Branch]:
        result = await self.db.execute(
            select(Branch)
            .where(Branch.company_id == self.company_id)
            .order_by(Branch.created_at)
        )
        return list(result.scalars().all())

    async def get_branch_by_id(self, branch_id: UUID) -> Branch | None:
        result = await self.db.execute(
            select(Branch).where(
                Branch.id == branch_id,
                Branch.company_id == self.company_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_services(
        self,
        *,
        active_only: bool = False,
        member_id: UUID | None = None,
    ) -> list[CompanyService]:
        query = (
            select(CompanyService)
            .where(CompanyService.company_id == self.company_id)
            .order_by(CompanyService.created_at.desc())
        )
        if active_only:
            query = query.where(CompanyService.is_active.is_(True))
        if member_id is not None:
            query = query.where(
                (CompanyService.member_id.is_(None)) | (CompanyService.member_id == member_id)
            )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_service_by_id(self, service_id: UUID) -> CompanyService | None:
        result = await self.db.execute(
            select(CompanyService).where(
                CompanyService.id == service_id,
                CompanyService.company_id == self.company_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_member_appointments(
        self,
        member_id: UUID,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
        statuses: list[AppointmentStatus] | None = None,
    ) -> list[MemberAppointment]:
        query = (
            select(MemberAppointment)
            .options(selectinload(MemberAppointment.service))
            .where(
                MemberAppointment.member_id == member_id,
                MemberAppointment.company_id == self.company_id,
            )
            .order_by(MemberAppointment.starts_at)
        )
        if from_date is not None:
            query = query.where(MemberAppointment.starts_at >= datetime.combine(from_date, time.min))
        if to_date is not None:
            query = query.where(
                MemberAppointment.starts_at < datetime.combine(to_date + timedelta(days=1), time.min)
            )
        if statuses:
            query = query.where(MemberAppointment.status.in_(statuses))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_member_appointment(
        self, member_id: UUID, appointment_id: UUID
    ) -> MemberAppointment | None:
        result = await self.db.execute(
            select(MemberAppointment)
            .options(selectinload(MemberAppointment.service))
            .where(
                MemberAppointment.id == appointment_id,
                MemberAppointment.member_id == member_id,
                MemberAppointment.company_id == self.company_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_member_by_id(self, member_id: UUID) -> CompanyMember | None:
        result = await self.db.execute(
            select(CompanyMember)
            .options(selectinload(CompanyMember.role))
            .where(
                CompanyMember.id == member_id,
                CompanyMember.company_id == self.company_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_member_schedules(self, member_id: UUID) -> list[MemberWorkSchedule]:
        result = await self.db.execute(
            select(MemberWorkSchedule)
            .where(
                MemberWorkSchedule.member_id == member_id,
                MemberWorkSchedule.company_id == self.company_id,
            )
            .order_by(MemberWorkSchedule.date_from.desc())
        )
        return list(result.scalars().all())

    async def get_member_schedule(
        self, member_id: UUID, schedule_id: UUID
    ) -> MemberWorkSchedule | None:
        result = await self.db.execute(
            select(MemberWorkSchedule).where(
                MemberWorkSchedule.id == schedule_id,
                MemberWorkSchedule.member_id == member_id,
                MemberWorkSchedule.company_id == self.company_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_member_schedule_exceptions(
        self,
        member_id: UUID,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[MemberScheduleException]:
        query = (
            select(MemberScheduleException)
            .where(
                MemberScheduleException.member_id == member_id,
                MemberScheduleException.company_id == self.company_id,
            )
            .order_by(MemberScheduleException.exception_date, MemberScheduleException.created_at)
        )
        if from_date is not None:
            query = query.where(
                func.coalesce(
                    MemberScheduleException.exception_date_to,
                    MemberScheduleException.exception_date,
                )
                >= from_date
            )
        if to_date is not None:
            query = query.where(MemberScheduleException.exception_date <= to_date)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_member_day_offs(self, member_id: UUID) -> list[MemberScheduleException]:
        result = await self.db.execute(
            select(MemberScheduleException).where(
                MemberScheduleException.member_id == member_id,
                MemberScheduleException.company_id == self.company_id,
                MemberScheduleException.kind == ScheduleExceptionKind.DAY_OFF,
            )
        )
        return list(result.scalars().all())

    async def get_member_schedule_exception(
        self, member_id: UUID, exception_id: UUID
    ) -> MemberScheduleException | None:
        result = await self.db.execute(
            select(MemberScheduleException).where(
                MemberScheduleException.id == exception_id,
                MemberScheduleException.member_id == member_id,
                MemberScheduleException.company_id == self.company_id,
            )
        )
        return result.scalar_one_or_none()

    async def count_entities(self) -> tuple[int, int, int]:
        users = await self.db.scalar(
            select(func.count())
            .select_from(CompanyMember)
            .where(CompanyMember.company_id == self.company_id)
        )
        branches = await self.db.scalar(
            select(func.count()).select_from(Branch).where(Branch.company_id == self.company_id)
        )
        roles = await self.db.scalar(
            select(func.count())
            .select_from(CompanyRole)
            .where(CompanyRole.company_id == self.company_id)
        )
        return users or 0, branches or 0, roles or 0

    async def get_active_subscription(self) -> UserSubscription | None:
        from app.services.subscription_service import get_company_subscription

        return await get_company_subscription(self.db, self.company_id)
