from calendar import monthrange
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.entities import AppointmentStatus, CompanyService, MemberAppointment


def resolve_statistics_period(
    *,
    day: date | None = None,
    month: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> tuple[date, date]:
    modes = sum(
        [
            day is not None,
            month is not None,
            from_date is not None or to_date is not None,
        ]
    )
    if modes > 1:
        raise AppError("Укажите один период: date, month или from_date/to_date")

    if day is not None:
        return day, day

    if month is not None:
        try:
            year_str, month_str = month.split("-", 1)
            year, month_num = int(year_str), int(month_str)
            if month_num < 1 or month_num > 12:
                raise ValueError
            last_day = monthrange(year, month_num)[1]
            return date(year, month_num, 1), date(year, month_num, last_day)
        except ValueError as exc:
            raise AppError("month должен быть в формате YYYY-MM") from exc

    if from_date is not None or to_date is not None:
        if from_date is None or to_date is None:
            raise AppError("Для диапазона укажите from_date и to_date")
        if to_date < from_date:
            raise AppError("to_date не может быть раньше from_date")
        if (to_date - from_date).days > 366:
            raise AppError("Диапазон не более 366 дней")
        return from_date, to_date

    today = datetime.now(UTC).date()
    first = today.replace(day=1)
    last_day = monthrange(today.year, today.month)[1]
    return first, today.replace(day=last_day)


def _period_bounds(period_from: date, period_to: date) -> tuple[datetime, datetime]:
    start = datetime.combine(period_from, datetime.min.time(), tzinfo=UTC)
    end = datetime.combine(period_to + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
    return start, end


async def get_dashboard_statistics(
    db: AsyncSession,
    company_id: UUID,
    *,
    period_from: date,
    period_to: date,
) -> dict:
    start, end = _period_bounds(period_from, period_to)
    base = (
        MemberAppointment.company_id == company_id,
        MemberAppointment.starts_at >= start,
        MemberAppointment.starts_at < end,
    )

    totals = await db.execute(
        select(
            func.count().filter(MemberAppointment.status != AppointmentStatus.CANCELLED),
            func.count().filter(MemberAppointment.status == AppointmentStatus.SCHEDULED),
            func.count().filter(MemberAppointment.status == AppointmentStatus.COMPLETED),
            func.count().filter(MemberAppointment.status == AppointmentStatus.CANCELLED),
        ).where(*base)
    )
    appointments_count, scheduled_count, completed_count, cancelled_count = totals.one()

    revenue_result = await db.scalar(
        select(func.coalesce(func.sum(func.coalesce(CompanyService.price, 0)), 0))
        .select_from(MemberAppointment)
        .join(CompanyService, CompanyService.id == MemberAppointment.service_id)
        .where(
            *base,
            MemberAppointment.status == AppointmentStatus.COMPLETED,
        )
    )
    revenue = int(revenue_result or 0)

    by_day: list[dict] = []
    if period_from != period_to:
        day_expr = func.date(MemberAppointment.starts_at)
        rows = await db.execute(
            select(
                day_expr.label("day"),
                func.count().filter(MemberAppointment.status != AppointmentStatus.CANCELLED),
                func.count().filter(MemberAppointment.status == AppointmentStatus.COMPLETED),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                MemberAppointment.status == AppointmentStatus.COMPLETED,
                                func.coalesce(CompanyService.price, 0),
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
            )
            .select_from(MemberAppointment)
            .outerjoin(CompanyService, CompanyService.id == MemberAppointment.service_id)
            .where(*base)
            .group_by(day_expr)
            .order_by(day_expr)
        )
        by_day = [
            {
                "date": row.day,
                "appointments_count": row[1] or 0,
                "completed_services_count": row[2] or 0,
                "revenue": int(row[3] or 0),
            }
            for row in rows.all()
        ]

    return {
        "period_from": period_from,
        "period_to": period_to,
        "appointments_count": appointments_count or 0,
        "scheduled_count": scheduled_count or 0,
        "completed_services_count": completed_count or 0,
        "cancelled_count": cancelled_count or 0,
        "revenue": revenue,
        "by_day": by_day,
    }
