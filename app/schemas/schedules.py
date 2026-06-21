from datetime import date, time
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.entities import SchedulePatternType

MAX_EXCEPTION_SPAN_DAYS = 365


class WeeklyPatternConfig(BaseModel):
    weekday_off: list[int] = Field(default_factory=list, description="0=пн … 6=вс")
    extra_off_dates: list[str] = Field(default_factory=list)
    extra_work_dates: list[str] = Field(default_factory=list)


class CyclePatternConfig(BaseModel):
    work_days: int = Field(ge=1, description="Рабочих дней в цикле, напр. 2 для 2/2")
    rest_days: int = Field(ge=1, description="Выходных в цикле, напр. 2 для 2/2")
    anchor_date: date = Field(description="Дата начала цикла")


class ManualPatternConfig(BaseModel):
    days: dict[str, bool] = Field(default_factory=dict, description="YYYY-MM-DD → рабочий день")


class WorkScheduleCreate(BaseModel):
    date_from: date
    date_to: date
    time_start: time
    time_end: time
    slot_interval_minutes: int = Field(ge=5, le=480)
    pattern_type: SchedulePatternType
    pattern_config: dict[str, Any]

    @field_validator("time_end")
    @classmethod
    def end_after_start(cls, v: time, info) -> time:
        start = info.data.get("time_start")
        if start and v <= start:
            raise ValueError("time_end должен быть позже time_start")
        return v


class WorkScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    member_id: UUID
    date_from: date
    date_to: date
    time_start: time
    time_end: time
    slot_interval_minutes: int
    pattern_type: SchedulePatternType
    pattern_config: dict[str, Any]
    created_by_id: UUID
    created_at: Any


class WorkScheduleSlotsResponse(BaseModel):
    schedule_id: UUID
    member_id: UUID
    from_date: date
    to_date: date
    service_id: UUID | None = None
    booking_duration_minutes: int | None = None
    buffer_before_minutes: int | None = None
    buffer_after_minutes: int | None = None
    slots_by_day: dict[str, list[str]]


class ScheduleExceptionCreate(BaseModel):
    """Один день: exception_date. Диапазон: date_from + date_to. Несколько дней: dates"""

    exception_date: date | None = None
    date_from: date | None = None
    date_to: date | None = None
    dates: list[date] | None = None
    kind: Literal["day_off", "slot_block"]
    block_config: dict[str, Any] | None = None
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_date_modes(self) -> "ScheduleExceptionCreate":
        has_single = self.exception_date is not None
        has_range = self.date_from is not None or self.date_to is not None
        has_list = bool(self.dates)

        modes = sum([has_single, has_range, has_list])
        if modes == 0:
            raise ValueError("Укажите exception_date, date_from/date_to или dates")
        if modes > 1:
            raise ValueError("Используйте только один способ: день, диапазон или список dates")

        if has_range:
            if self.date_from is None or self.date_to is None:
                raise ValueError("Для диапазона нужны date_from и date_to")
            if self.date_to < self.date_from:
                raise ValueError("date_to не может быть раньше date_from")
            if (self.date_to - self.date_from).days > MAX_EXCEPTION_SPAN_DAYS:
                raise ValueError(f"Диапазон дат не более {MAX_EXCEPTION_SPAN_DAYS} дней")

        if has_list and self.dates:
            unique_dates = sorted(set(self.dates))
            if len(unique_dates) > MAX_EXCEPTION_SPAN_DAYS + 1:
                raise ValueError(f"Не более {MAX_EXCEPTION_SPAN_DAYS + 1} дат в списке")
            span = (unique_dates[-1] - unique_dates[0]).days
            if span > MAX_EXCEPTION_SPAN_DAYS:
                raise ValueError(f"Размах дат в списке не более {MAX_EXCEPTION_SPAN_DAYS} дней")
            self.dates = unique_dates

        return self


class ScheduleExceptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    member_id: UUID
    exception_date: date
    exception_date_to: date | None
    exception_dates: list[str] | None
    kind: Literal["day_off", "slot_block"]
    block_config: dict[str, Any] | None
    note: str | None
    created_by_id: UUID
    created_at: Any
