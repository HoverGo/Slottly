from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DashboardDailyStat(BaseModel):
    date: date
    appointments_count: int
    completed_services_count: int
    revenue: int


class DashboardStatisticsResponse(BaseModel):
    period_from: date
    period_to: date
    appointments_count: int = Field(description="Записи кроме отменённых")
    scheduled_count: int
    completed_services_count: int
    cancelled_count: int
    revenue: int = Field(description="Выручка по выполненным услугам (сумма цен услуг)")
    by_day: list[DashboardDailyStat] = Field(default_factory=list)
