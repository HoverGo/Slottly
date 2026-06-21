from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Iterable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.permissions import ALL_PERMISSIONS
from app.core.tenant import TenantContext
from app.models.entities import (
    AppointmentStatus,
    MemberAppointment,
    MemberScheduleException,
    MemberWorkSchedule,
    ScheduleExceptionKind,
    SchedulePatternType,
)
from app.repositories.tenant_repository import TenantRepository

MAX_SCHEDULE_DAYS = 365
MAX_EXCEPTION_SPAN_DAYS = 365


class ResolvedExceptionDates:
    __slots__ = ("exception_date", "exception_date_to", "exception_dates")

    def __init__(
        self,
        exception_date: date,
        exception_date_to: date | None,
        exception_dates: list[str] | None,
    ) -> None:
        self.exception_date = exception_date
        self.exception_date_to = exception_date_to
        self.exception_dates = exception_dates


def resolve_exception_dates(
    *,
    exception_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    dates: list[date] | None = None,
) -> ResolvedExceptionDates:
    if dates:
        unique = sorted(set(dates))
        iso_dates = [day.isoformat() for day in unique]
        span = (unique[-1] - unique[0]).days
        if span > MAX_EXCEPTION_SPAN_DAYS:
            raise AppError(f"Размах дат в списке не более {MAX_EXCEPTION_SPAN_DAYS} дней")
        return ResolvedExceptionDates(unique[0], unique[-1], iso_dates)

    if date_from is not None and date_to is not None:
        if date_to < date_from:
            raise AppError("date_to не может быть раньше date_from")
        if (date_to - date_from).days > MAX_EXCEPTION_SPAN_DAYS:
            raise AppError(f"Диапазон дат не более {MAX_EXCEPTION_SPAN_DAYS} дней")
        return ResolvedExceptionDates(date_from, date_to, None)

    day = exception_date or date_from
    if day is None:
        raise AppError("Укажите exception_date, date_from/date_to или dates")
    return ResolvedExceptionDates(day, None, None)


def iter_exception_days(
    exception_date: date,
    exception_date_to: date | None = None,
    exception_dates: list[str] | None = None,
) -> Iterable[date]:
    if exception_dates:
        for day_str in exception_dates:
            yield date.fromisoformat(day_str)
        return

    end = exception_date_to or exception_date
    current = exception_date
    while current <= end:
        yield current
        current += timedelta(days=1)


def exception_covers_day(
    exception: MemberScheduleException,
    day: date,
) -> bool:
    if exception.exception_dates:
        return day.isoformat() in exception.exception_dates

    end = exception.exception_date_to or exception.exception_date
    return exception.exception_date <= day <= end


def validate_permissions(permissions: list[str]) -> list[str]:
    invalid = set(permissions) - ALL_PERMISSIONS
    if invalid:
        raise AppError(f"Неизвестные права: {', '.join(sorted(invalid))}")
    return list(dict.fromkeys(permissions))


def _validate_period(date_from: date, date_to: date) -> None:
    if date_to < date_from:
        raise AppError("date_to не может быть раньше date_from")
    if (date_to - date_from).days > MAX_SCHEDULE_DAYS:
        raise AppError(f"Максимальный период расписания — {MAX_SCHEDULE_DAYS} дней")


def _validate_time_window(time_start: time, time_end: time, interval: int) -> None:
    if interval < 5 or interval > 480:
        raise AppError("Интервал между записями: от 5 до 480 минут")
    start_mins = time_start.hour * 60 + time_start.minute
    end_mins = time_end.hour * 60 + time_end.minute
    if end_mins <= start_mins:
        raise AppError("time_end должен быть позже time_start")


def validate_pattern_config(pattern_type: SchedulePatternType, config: dict[str, Any]) -> dict[str, Any]:
    if pattern_type == SchedulePatternType.WEEKLY:
        weekday_off = config.get("weekday_off", [])
        if not isinstance(weekday_off, list):
            raise AppError("weekday_off должен быть списком")
        for d in weekday_off:
            if not isinstance(d, int) or d < 0 or d > 6:
                raise AppError("weekday_off: дни 0 (пн) — 6 (вс)")
        return {
            "weekday_off": weekday_off,
            "extra_off_dates": config.get("extra_off_dates", []),
            "extra_work_dates": config.get("extra_work_dates", []),
        }
    if pattern_type == SchedulePatternType.CYCLE:
        work_days = config.get("work_days")
        rest_days = config.get("rest_days")
        anchor = config.get("anchor_date")
        if not work_days or not rest_days or not anchor:
            raise AppError("Для cycle нужны work_days, rest_days, anchor_date")
        if work_days < 1 or rest_days < 1:
            raise AppError("work_days и rest_days должны быть ≥ 1")
        return {
            "work_days": int(work_days),
            "rest_days": int(rest_days),
            "anchor_date": str(anchor),
        }
    if pattern_type == SchedulePatternType.MANUAL:
        days = config.get("days", {})
        if not isinstance(days, dict):
            raise AppError("days должен быть объектом дата → true/false")
        return {"days": {str(k): bool(v) for k, v in days.items()}}
    raise AppError("Неизвестный тип паттерна")


def _time_to_str(value: time) -> str:
    return value.strftime("%H:%M")


def _parse_time_str(value: str) -> time:
    parts = value.split(":")
    if len(parts) != 2:
        raise AppError("Время должно быть в формате HH:MM")
    hour, minute = int(parts[0]), int(parts[1])
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise AppError("Некорректное время")
    return time(hour, minute)


def validate_block_config(config: dict[str, Any]) -> dict[str, Any]:
    mode = config.get("mode")
    if mode == "range":
        time_from = config.get("time_from")
        time_to = config.get("time_to")
        if not time_from or not time_to:
            raise AppError("Для диапазона нужны time_from и time_to")
        t_from = _parse_time_str(str(time_from)[:5])
        t_to = _parse_time_str(str(time_to)[:5])
        if t_to <= t_from:
            raise AppError("time_to должен быть позже time_from")
        return {"mode": "range", "time_from": _time_to_str(t_from), "time_to": _time_to_str(t_to)}
    if mode == "times":
        times = config.get("times", [])
        if not isinstance(times, list) or not times:
            raise AppError("times должен быть непустым списком времён HH:MM")
        normalized: list[str] = []
        for item in times:
            normalized.append(_time_to_str(_parse_time_str(str(item)[:5])))
        return {"mode": "times", "times": list(dict.fromkeys(normalized))}
    raise AppError("block_config.mode: range или times")


def _slot_blocked(slot_dt: datetime, block_config: dict[str, Any]) -> bool:
    mode = block_config.get("mode")
    if mode == "range":
        slot_time = slot_dt.time()
        t_from = _parse_time_str(block_config["time_from"])
        t_to = _parse_time_str(block_config["time_to"])
        return t_from <= slot_time < t_to
    if mode == "times":
        return slot_dt.strftime("%H:%M") in set(block_config.get("times", []))
    return False


def normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


def get_appointment_end(appointment: MemberAppointment) -> datetime:
    start = normalize_datetime(appointment.starts_at)
    return start + timedelta(minutes=appointment.duration_minutes)


def get_appointment_blocked_interval(appointment: MemberAppointment) -> tuple[datetime, datetime]:
    start = normalize_datetime(appointment.starts_at)
    blocked_start = start - timedelta(minutes=appointment.buffer_before_minutes)
    blocked_end = start + timedelta(
        minutes=appointment.duration_minutes + appointment.buffer_after_minutes
    )
    return blocked_start, blocked_end


def intervals_overlap(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    a0, a1 = normalize_datetime(start_a), normalize_datetime(end_a)
    b0, b1 = normalize_datetime(start_b), normalize_datetime(end_b)
    return a0 < b1 and a1 > b0


def filter_slots_by_appointments(
    slots: list[datetime],
    appointments: list[MemberAppointment],
    *,
    duration_minutes: int,
    buffer_before_minutes: int = 0,
    buffer_after_minutes: int = 0,
    day_start: datetime,
    day_end: datetime,
) -> list[datetime]:
    active = [a for a in appointments if a.status != AppointmentStatus.CANCELLED]

    result: list[datetime] = []
    for slot in slots:
        blocked_start = slot - timedelta(minutes=buffer_before_minutes)
        blocked_end = slot + timedelta(minutes=duration_minutes + buffer_after_minutes)
        if blocked_start < day_start or blocked_end > day_end:
            continue
        blocked = any(
            intervals_overlap(
                blocked_start,
                blocked_end,
                *get_appointment_blocked_interval(apt),
            )
            for apt in active
        )
        if not blocked:
            result.append(slot)
    return result


def apply_schedule_exceptions(
    day: date,
    slots: list[datetime],
    exceptions: list[MemberScheduleException],
) -> list[datetime]:
    day_exceptions = [e for e in exceptions if exception_covers_day(e, day)]
    if any(e.kind == ScheduleExceptionKind.DAY_OFF for e in day_exceptions):
        return []

    block_configs = [
        e.block_config
        for e in day_exceptions
        if e.kind == ScheduleExceptionKind.SLOT_BLOCK and e.block_config
    ]
    if not block_configs:
        return slots

    return [slot for slot in slots if not any(_slot_blocked(slot, cfg) for cfg in block_configs)]


def is_working_day(schedule: MemberWorkSchedule, day: date) -> bool:
    if day < schedule.date_from or day > schedule.date_to:
        return False

    config = schedule.pattern_config
    day_str = day.isoformat()

    if schedule.pattern_type == SchedulePatternType.WEEKLY:
        if day_str in config.get("extra_off_dates", []):
            return False
        if day_str in config.get("extra_work_dates", []):
            return True
        weekday = day.weekday()
        return weekday not in config.get("weekday_off", [])

    if schedule.pattern_type == SchedulePatternType.CYCLE:
        anchor = date.fromisoformat(config["anchor_date"])
        work_days = config["work_days"]
        rest_days = config["rest_days"]
        cycle_len = work_days + rest_days
        delta = (day - anchor).days
        if delta < 0:
            return False
        pos = delta % cycle_len
        return pos < work_days

    if schedule.pattern_type == SchedulePatternType.MANUAL:
        days = config.get("days", {})
        if day_str not in days:
            return False
        return bool(days[day_str])

    return False


def generate_slots_for_day(
    schedule: MemberWorkSchedule,
    day: date,
    exceptions: list[MemberScheduleException] | None = None,
    appointments: list[MemberAppointment] | None = None,
    booking_duration_minutes: int | None = None,
    buffer_before_minutes: int = 0,
    buffer_after_minutes: int = 0,
) -> list[datetime]:
    if not is_working_day(schedule, day):
        return []

    slots: list[datetime] = []
    current = datetime.combine(day, schedule.time_start)
    end = datetime.combine(day, schedule.time_end)
    delta = timedelta(minutes=schedule.slot_interval_minutes)

    while current + delta <= end:
        slots.append(current)
        current += delta

    if exceptions:
        slots = apply_schedule_exceptions(day, slots, exceptions)

    duration = booking_duration_minutes or schedule.slot_interval_minutes
    day_start = datetime.combine(day, schedule.time_start)
    day_end = datetime.combine(day, schedule.time_end)
    day_appointments = [
        a for a in (appointments or []) if normalize_datetime(a.starts_at).date() == day
    ]
    if appointments or booking_duration_minutes is not None:
        slots = filter_slots_by_appointments(
            slots,
            day_appointments,
            duration_minutes=duration,
            buffer_before_minutes=buffer_before_minutes if booking_duration_minutes else 0,
            buffer_after_minutes=buffer_after_minutes if booking_duration_minutes else 0,
            day_start=day_start,
            day_end=day_end,
        )

    return slots


def generate_slots_range(
    schedule: MemberWorkSchedule,
    from_date: date,
    to_date: date,
    exceptions: list[MemberScheduleException] | None = None,
    appointments: list[MemberAppointment] | None = None,
    booking_duration_minutes: int | None = None,
    buffer_before_minutes: int = 0,
    buffer_after_minutes: int = 0,
) -> dict[str, list[str]]:
    if to_date < from_date:
        raise AppError("to_date не может быть раньше from_date")

    result: dict[str, list[str]] = {}
    current = max(from_date, schedule.date_from)
    end = min(to_date, schedule.date_to)

    while current <= end:
        day_slots = generate_slots_for_day(
            schedule,
            current,
            exceptions,
            appointments=appointments,
            booking_duration_minutes=booking_duration_minutes,
            buffer_before_minutes=buffer_before_minutes,
            buffer_after_minutes=buffer_after_minutes,
        )
        if day_slots:
            result[current.isoformat()] = [s.strftime("%H:%M") for s in day_slots]
        current += timedelta(days=1)

    return result


async def create_work_schedule(
    db: AsyncSession,
    tenant: TenantContext,
    member_id: UUID,
    *,
    date_from: date,
    date_to: date,
    time_start: time,
    time_end: time,
    slot_interval_minutes: int,
    pattern_type: SchedulePatternType,
    pattern_config: dict[str, Any],
) -> MemberWorkSchedule:
    from app.services.company_service import require_active_subscription

    await require_active_subscription(db, tenant.company)

    repo = TenantRepository(db, tenant.company_id)
    member = await repo.get_member_by_id(member_id)
    if not member:
        raise NotFoundError("Сотрудник не найден в компании")

    _validate_period(date_from, date_to)
    _validate_time_window(time_start, time_end, slot_interval_minutes)
    validated_config = validate_pattern_config(pattern_type, pattern_config)

    schedule = MemberWorkSchedule(
        company_id=tenant.company_id,
        member_id=member.id,
        date_from=date_from,
        date_to=date_to,
        time_start=time_start,
        time_end=time_end,
        slot_interval_minutes=slot_interval_minutes,
        pattern_type=pattern_type,
        pattern_config=validated_config,
        created_by_id=tenant.user_id,
    )
    db.add(schedule)
    await db.flush()
    return schedule


async def list_member_schedules(
    db: AsyncSession, company_id: UUID, member_id: UUID
) -> list[MemberWorkSchedule]:
    repo = TenantRepository(db, company_id)
    member = await repo.get_member_by_id(member_id)
    if not member:
        raise NotFoundError("Сотрудник не найден в компании")
    return await repo.list_member_schedules(member_id)


async def get_member_schedule(
    db: AsyncSession, company_id: UUID, member_id: UUID, schedule_id: UUID
) -> MemberWorkSchedule:
    repo = TenantRepository(db, company_id)
    schedule = await repo.get_member_schedule(member_id, schedule_id)
    if not schedule:
        raise NotFoundError("Расписание не найдено")
    return schedule


async def create_schedule_exception(
    db: AsyncSession,
    tenant: TenantContext,
    member_id: UUID,
    *,
    kind: ScheduleExceptionKind,
    block_config: dict[str, Any] | None = None,
    note: str | None = None,
    exception_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    dates: list[date] | None = None,
) -> MemberScheduleException:
    from app.services.company_service import require_active_subscription

    await require_active_subscription(db, tenant.company)

    repo = TenantRepository(db, tenant.company_id)
    member = await repo.get_member_by_id(member_id)
    if not member:
        raise NotFoundError("Сотрудник не найден в компании")

    resolved = resolve_exception_dates(
        exception_date=exception_date,
        date_from=date_from,
        date_to=date_to,
        dates=dates,
    )

    validated_config: dict[str, Any] | None = None
    if kind == ScheduleExceptionKind.DAY_OFF:
        if block_config:
            raise AppError("Для выходного дня block_config не нужен")
        existing_day_offs = await repo.list_member_day_offs(member_id)
        new_days = set(
            iter_exception_days(
                resolved.exception_date,
                resolved.exception_date_to,
                resolved.exception_dates,
            )
        )
        for existing in existing_day_offs:
            for day in new_days:
                if exception_covers_day(existing, day):
                    raise ConflictError(f"Выходной уже назначен на {day.isoformat()}")
    elif kind == ScheduleExceptionKind.SLOT_BLOCK:
        if not block_config:
            raise AppError("Для блокировки слотов нужен block_config")
        validated_config = validate_block_config(block_config)
    else:
        raise AppError("Неизвестный тип исключения")

    exception = MemberScheduleException(
        company_id=tenant.company_id,
        member_id=member.id,
        exception_date=resolved.exception_date,
        exception_date_to=resolved.exception_date_to,
        exception_dates=resolved.exception_dates,
        kind=kind,
        block_config=validated_config,
        note=note,
        created_by_id=tenant.user_id,
    )
    db.add(exception)
    await db.flush()
    return exception


async def list_schedule_exceptions(
    db: AsyncSession,
    company_id: UUID,
    member_id: UUID,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[MemberScheduleException]:
    repo = TenantRepository(db, company_id)
    member = await repo.get_member_by_id(member_id)
    if not member:
        raise NotFoundError("Сотрудник не найден в компании")
    return await repo.list_member_schedule_exceptions(member_id, from_date=from_date, to_date=to_date)


async def delete_schedule_exception(
    db: AsyncSession,
    tenant: TenantContext,
    member_id: UUID,
    exception_id: UUID,
) -> None:
    from app.services.company_service import require_active_subscription

    await require_active_subscription(db, tenant.company)

    repo = TenantRepository(db, tenant.company_id)
    exception = await repo.get_member_schedule_exception(member_id, exception_id)
    if not exception:
        raise NotFoundError("Исключение не найдено")
    await db.delete(exception)
