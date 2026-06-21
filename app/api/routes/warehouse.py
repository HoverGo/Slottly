from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_company_tenant, require_permission
from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.permissions import MANAGE_WAREHOUSE
from app.core.tenant import TenantContext
from app.repositories.warehouse_repository import WarehouseRepository
from app.schemas.warehouse import (
    StockMovementCreate,
    StockMovementResponse,
    WarehouseItemCreate,
    WarehouseItemResponse,
    WarehouseItemUpdate,
    WarehouseStockRowResponse,
)
from app.services.warehouse_service import (
    create_stock_movement,
    create_warehouse_item,
    get_warehouse_item,
    item_to_response,
    list_stock_movements,
    list_stock_rows,
    list_warehouse_items,
    movement_to_response,
    stock_row_to_response,
    update_warehouse_item,
)

router = APIRouter(prefix="/companies/{company_id}/warehouse", tags=["warehouse"])


async def _branch_names(db: AsyncSession, company_id: UUID) -> dict[UUID, str]:
    repo = WarehouseRepository(db, company_id)
    return await repo.get_branch_name_map()


@router.post("/items", response_model=WarehouseItemResponse, status_code=201)
async def create_item(
    data: WarehouseItemCreate,
    tenant: TenantContext = Depends(require_permission(MANAGE_WAREHOUSE)),
    db: AsyncSession = Depends(get_db),
) -> WarehouseItemResponse:
    try:
        item = await create_warehouse_item(
            db,
            tenant,
            name=data.name,
            item_type=data.item_type,
            sku=data.sku,
            unit=data.unit,
            description=data.description,
            min_quantity=data.min_quantity,
            initial_quantity=data.initial_quantity,
            branch_id=data.branch_id,
        )
        names = await _branch_names(db, tenant.company_id)
        return WarehouseItemResponse(**item_to_response(item, names))
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/items", response_model=list[WarehouseItemResponse])
async def list_items(
    item_type: str | None = Query(default=None, pattern="^(product|consumable)$"),
    active_only: bool = Query(default=False),
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[WarehouseItemResponse]:
    items = await list_warehouse_items(
        db, tenant.company_id, item_type=item_type, active_only=active_only
    )
    names = await _branch_names(db, tenant.company_id)
    return [WarehouseItemResponse(**item_to_response(item, names)) for item in items]


@router.get("/items/{item_id}", response_model=WarehouseItemResponse)
async def get_item(
    item_id: UUID,
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
) -> WarehouseItemResponse:
    try:
        item = await get_warehouse_item(db, tenant.company_id, item_id)
        names = await _branch_names(db, tenant.company_id)
        return WarehouseItemResponse(**item_to_response(item, names))
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.patch("/items/{item_id}", response_model=WarehouseItemResponse)
async def patch_item(
    item_id: UUID,
    data: WarehouseItemUpdate,
    tenant: TenantContext = Depends(require_permission(MANAGE_WAREHOUSE)),
    db: AsyncSession = Depends(get_db),
) -> WarehouseItemResponse:
    try:
        item = await update_warehouse_item(
            db,
            tenant,
            item_id,
            name=data.name,
            sku=data.sku,
            unit=data.unit,
            description=data.description,
            min_quantity=data.min_quantity,
            is_active=data.is_active,
            clear_sku=data.clear_sku,
            clear_min_quantity=data.clear_min_quantity,
        )
        names = await _branch_names(db, tenant.company_id)
        return WarehouseItemResponse(**item_to_response(item, names))
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/stock", response_model=list[WarehouseStockRowResponse])
async def list_stock(
    item_type: str | None = Query(default=None, pattern="^(product|consumable)$"),
    branch_id: UUID | None = Query(default=None),
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[WarehouseStockRowResponse]:
    try:
        rows = await list_stock_rows(
            db, tenant.company_id, item_type=item_type, branch_id=branch_id
        )
        names = await _branch_names(db, tenant.company_id)
        return [WarehouseStockRowResponse(**stock_row_to_response(row, names)) for row in rows]
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/movements", response_model=StockMovementResponse, status_code=201)
async def create_movement(
    data: StockMovementCreate,
    tenant: TenantContext = Depends(require_permission(MANAGE_WAREHOUSE)),
    db: AsyncSession = Depends(get_db),
) -> StockMovementResponse:
    try:
        movement = await create_stock_movement(
            db,
            tenant,
            item_id=data.item_id,
            movement_type=data.movement_type,
            quantity=data.quantity,
            quantity_delta=data.quantity_delta,
            branch_id=data.branch_id,
            from_branch_id=data.from_branch_id,
            to_branch_id=data.to_branch_id,
            note=data.note,
        )
        names = await _branch_names(db, tenant.company_id)
        return StockMovementResponse(**movement_to_response(movement, names))
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/movements", response_model=list[StockMovementResponse])
async def list_movements(
    item_id: UUID | None = Query(default=None),
    movement_type: str | None = Query(
        default=None, pattern="^(receipt|issue|adjustment|transfer)$"
    ),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    tenant: TenantContext = Depends(get_company_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[StockMovementResponse]:
    movements = await list_stock_movements(
        db,
        tenant.company_id,
        item_id=item_id,
        movement_type=movement_type,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
    )
    names = await _branch_names(db, tenant.company_id)
    return [StockMovementResponse(**movement_to_response(m, names)) for m in movements]
