from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.tenant import TenantContext
from app.models.entities import StockMovementType, WarehouseItem, WarehouseItemType, WarehouseMovement, WarehouseStock
from app.repositories.warehouse_repository import WarehouseRepository


def _branch_label(branch_id: UUID | None, names: dict[UUID, str]) -> str | None:
    if branch_id is None:
        return "Основной склад"
    return names.get(branch_id)


def _item_total_quantity(item: WarehouseItem) -> int:
    return sum(balance.quantity for balance in item.stock_balances)


def item_to_response(item: WarehouseItem, branch_names: dict[UUID, str]) -> dict:
    stock = [
        {
            "branch_id": balance.branch_id,
            "branch_name": _branch_label(balance.branch_id, branch_names),
            "quantity": balance.quantity,
        }
        for balance in sorted(item.stock_balances, key=lambda b: (b.branch_id is not None, str(b.branch_id)))
    ]
    total = sum(row["quantity"] for row in stock)
    return {
        "id": item.id,
        "company_id": item.company_id,
        "item_type": item.item_type.value,
        "name": item.name,
        "sku": item.sku,
        "unit": item.unit,
        "description": item.description,
        "min_quantity": item.min_quantity,
        "is_active": item.is_active,
        "total_quantity": total,
        "stock": stock,
        "is_low_stock": item.min_quantity is not None and total <= item.min_quantity,
        "created_by_id": item.created_by_id,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def movement_to_response(movement: WarehouseMovement, branch_names: dict[UUID, str]) -> dict:
    item = movement.item
    return {
        "id": movement.id,
        "company_id": movement.company_id,
        "item_id": movement.item_id,
        "item_name": item.name if item else "",
        "item_type": item.item_type.value if item else "product",
        "movement_type": movement.movement_type.value,
        "quantity": movement.quantity,
        "branch_id": movement.branch_id,
        "branch_name": _branch_label(movement.branch_id, branch_names),
        "from_branch_id": movement.from_branch_id,
        "from_branch_name": _branch_label(movement.from_branch_id, branch_names),
        "to_branch_id": movement.to_branch_id,
        "to_branch_name": _branch_label(movement.to_branch_id, branch_names),
        "quantity_before": movement.quantity_before,
        "quantity_after": movement.quantity_after,
        "note": movement.note,
        "created_by_id": movement.created_by_id,
        "created_at": movement.created_at,
    }


def stock_row_to_response(stock: WarehouseStock, branch_names: dict[UUID, str]) -> dict:
    item = stock.item
    return {
        "item_id": item.id,
        "item_name": item.name,
        "item_type": item.item_type.value,
        "sku": item.sku,
        "unit": item.unit,
        "branch_id": stock.branch_id,
        "branch_name": _branch_label(stock.branch_id, branch_names),
        "quantity": stock.quantity,
        "min_quantity": item.min_quantity,
        "is_low_stock": item.min_quantity is not None and stock.quantity <= item.min_quantity,
    }


async def _validate_branch(repo: WarehouseRepository, branch_id: UUID | None) -> None:
    if branch_id is None:
        return
    branch = await repo.get_branch_by_id(branch_id)
    if not branch:
        raise NotFoundError("Филиал не найден")


async def _get_or_create_stock(
    repo: WarehouseRepository,
    item_id: UUID,
    branch_id: UUID | None,
) -> WarehouseStock:
    stock = await repo.get_stock(item_id, branch_id)
    if stock:
        return stock
    stock = WarehouseStock(
        company_id=repo.company_id,
        item_id=item_id,
        branch_id=branch_id,
        quantity=0,
    )
    repo.db.add(stock)
    await repo.db.flush()
    return stock


async def _apply_stock_change(stock: WarehouseStock, delta: int) -> tuple[int, int]:
    before = stock.quantity
    after = before + delta
    if after < 0:
        raise AppError("Недостаточно остатка на складе")
    stock.quantity = after
    stock.updated_at = datetime.now(UTC)
    return before, after


async def create_warehouse_item(
    db: AsyncSession,
    tenant: TenantContext,
    *,
    name: str,
    item_type: str,
    sku: str | None = None,
    unit: str = "шт",
    description: str | None = None,
    min_quantity: int | None = None,
    initial_quantity: int | None = None,
    branch_id: UUID | None = None,
) -> WarehouseItem:
    from app.services.company_service import require_active_subscription

    await require_active_subscription(db, tenant.company)
    repo = WarehouseRepository(db, tenant.company_id)
    await _validate_branch(repo, branch_id)

    clean_sku = sku.strip() if sku and sku.strip() else None
    if clean_sku and await repo.get_item_by_sku(clean_sku):
        raise ConflictError("Артикул уже используется")

    item = WarehouseItem(
        company_id=tenant.company_id,
        item_type=WarehouseItemType(item_type),
        name=name.strip(),
        sku=clean_sku,
        unit=unit.strip() or "шт",
        description=description,
        min_quantity=min_quantity,
        created_by_id=tenant.user_id,
    )
    db.add(item)
    await db.flush()

    if initial_quantity and initial_quantity > 0:
        await create_stock_movement(
            db,
            tenant,
            item_id=item.id,
            movement_type="receipt",
            quantity=initial_quantity,
            branch_id=branch_id,
            note="Начальный остаток",
        )
        item = await repo.get_item_by_id(item.id)
        if not item:
            raise NotFoundError("Позиция не найдена")

    return item


async def update_warehouse_item(
    db: AsyncSession,
    tenant: TenantContext,
    item_id: UUID,
    *,
    name: str | None = None,
    sku: str | None = None,
    unit: str | None = None,
    description: str | None = None,
    min_quantity: int | None = None,
    is_active: bool | None = None,
    clear_sku: bool = False,
    clear_min_quantity: bool = False,
) -> WarehouseItem:
    repo = WarehouseRepository(db, tenant.company_id)
    item = await repo.get_item_by_id(item_id)
    if not item:
        raise NotFoundError("Позиция не найдена")

    if name is not None:
        item.name = name.strip()
    if clear_sku:
        item.sku = None
    elif sku is not None:
        clean_sku = sku.strip() if sku.strip() else None
        if clean_sku and clean_sku != item.sku:
            existing = await repo.get_item_by_sku(clean_sku)
            if existing and existing.id != item.id:
                raise ConflictError("Артикул уже используется")
        item.sku = clean_sku
    if unit is not None:
        item.unit = unit.strip() or item.unit
    if description is not None:
        item.description = description
    if clear_min_quantity:
        item.min_quantity = None
    elif min_quantity is not None:
        item.min_quantity = min_quantity
    if is_active is not None:
        item.is_active = is_active

    item.updated_at = datetime.now(UTC)
    await db.flush()
    reloaded = await repo.get_item_by_id(item.id)
    return reloaded or item


async def get_warehouse_item(db: AsyncSession, company_id: UUID, item_id: UUID) -> WarehouseItem:
    repo = WarehouseRepository(db, company_id)
    item = await repo.get_item_by_id(item_id)
    if not item:
        raise NotFoundError("Позиция не найдена")
    return item


async def list_warehouse_items(
    db: AsyncSession,
    company_id: UUID,
    *,
    item_type: str | None = None,
    active_only: bool = False,
) -> list[WarehouseItem]:
    repo = WarehouseRepository(db, company_id)
    return await repo.list_items(item_type=item_type, active_only=active_only)


async def list_stock_rows(
    db: AsyncSession,
    company_id: UUID,
    *,
    item_type: str | None = None,
    branch_id: UUID | None = None,
) -> list[WarehouseStock]:
    repo = WarehouseRepository(db, company_id)
    if branch_id is not None:
        await _validate_branch(repo, branch_id)
    return await repo.list_stock_rows(item_type=item_type, branch_id=branch_id)


async def list_stock_movements(
    db: AsyncSession,
    company_id: UUID,
    *,
    item_id: UUID | None = None,
    movement_type: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    limit: int = 100,
) -> list[WarehouseMovement]:
    repo = WarehouseRepository(db, company_id)
    return await repo.list_movements(
        item_id=item_id,
        movement_type=movement_type,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
    )


async def create_stock_movement(
    db: AsyncSession,
    tenant: TenantContext,
    *,
    item_id: UUID,
    movement_type: str,
    quantity: int | None = None,
    quantity_delta: int | None = None,
    branch_id: UUID | None = None,
    from_branch_id: UUID | None = None,
    to_branch_id: UUID | None = None,
    note: str | None = None,
) -> WarehouseMovement | list[WarehouseMovement]:
    from app.services.company_service import require_active_subscription

    await require_active_subscription(db, tenant.company)
    repo = WarehouseRepository(db, tenant.company_id)
    item = await repo.get_item_by_id(item_id)
    if not item:
        raise NotFoundError("Позиция не найдена")
    if not item.is_active and movement_type in ("issue", "transfer"):
        raise AppError("Позиция неактивна")

    movement_enum = StockMovementType(movement_type)

    if movement_enum == StockMovementType.TRANSFER:
        assert quantity is not None
        await _validate_branch(repo, from_branch_id)
        await _validate_branch(repo, to_branch_id)
        from_stock = await _get_or_create_stock(repo, item_id, from_branch_id)
        to_stock = await _get_or_create_stock(repo, item_id, to_branch_id)
        from_before, from_after = await _apply_stock_change(from_stock, -quantity)
        _, to_after = await _apply_stock_change(to_stock, quantity)
        movement = WarehouseMovement(
            company_id=tenant.company_id,
            item_id=item_id,
            movement_type=movement_enum,
            quantity=quantity,
            from_branch_id=from_branch_id,
            to_branch_id=to_branch_id,
            quantity_before=from_before,
            quantity_after=from_after,
            note=note,
            created_by_id=tenant.user_id,
        )
        db.add(movement)
        await db.flush()
        await db.refresh(movement, ["item"])
        return movement

    await _validate_branch(repo, branch_id)
    stock = await _get_or_create_stock(repo, item_id, branch_id)

    if movement_enum == StockMovementType.RECEIPT:
        assert quantity is not None
        before, after = await _apply_stock_change(stock, quantity)
        stored_quantity = quantity
    elif movement_enum == StockMovementType.ISSUE:
        assert quantity is not None
        before, after = await _apply_stock_change(stock, -quantity)
        stored_quantity = quantity
    elif movement_enum == StockMovementType.ADJUSTMENT:
        assert quantity_delta is not None
        before, after = await _apply_stock_change(stock, quantity_delta)
        stored_quantity = abs(quantity_delta)
    else:
        raise AppError("Неизвестный тип движения")

    movement = WarehouseMovement(
        company_id=tenant.company_id,
        item_id=item_id,
        movement_type=movement_enum,
        quantity=stored_quantity,
        branch_id=branch_id,
        quantity_before=before,
        quantity_after=after,
        note=note,
        created_by_id=tenant.user_id,
    )
    db.add(movement)
    await db.flush()
    await db.refresh(movement, ["item"])
    return movement
