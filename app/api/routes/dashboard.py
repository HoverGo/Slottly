from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_statistics_access
from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.tenant import TenantContext
from app.schemas.statistics import DashboardStatisticsResponse
from app.services.statistics_service import get_dashboard_statistics, resolve_statistics_period

router = APIRouter(prefix="/companies/{company_id}/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardStatisticsResponse)
async def get_dashboard(
    date_param: date | None = Query(default=None, alias="date", description="Статистика за день"),
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$", description="Месяц YYYY-MM"),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    tenant: TenantContext = Depends(require_statistics_access()),
    db: AsyncSession = Depends(get_db),
) -> DashboardStatisticsResponse:
    try:
        period_from, period_to = resolve_statistics_period(
            day=date_param,
            month=month,
            from_date=from_date,
            to_date=to_date,
        )
        stats = await get_dashboard_statistics(
            db,
            tenant.company_id,
            period_from=period_from,
            period_to=period_to,
        )
        return DashboardStatisticsResponse(**stats)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
