from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entities import Branch, StockMovementType, WarehouseItem, WarehouseMovement, WarehouseStock


class WarehouseRepository:
    def __init__(self, db: AsyncSession, company_id: UUID):
        self.db = db
        self.company_id = company_id

    async def get_branch_by_id(self, branch_id: UUID) -> Branch | None:
        result = await self.db.execute(
            select(Branch).where(
                Branch.id == branch_id,
                Branch.company_id == self.company_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_item_by_id(self, item_id: UUID) -> WarehouseItem | None:
        result = await self.db.execute(
            select(WarehouseItem)
            .options(selectinload(WarehouseItem.stock_balances).selectinload(WarehouseStock.branch))
            .where(
                WarehouseItem.id == item_id,
                WarehouseItem.company_id == self.company_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_item_by_sku(self, sku: str) -> WarehouseItem | None:
        result = await self.db.execute(
            select(WarehouseItem).where(
                WarehouseItem.company_id == self.company_id,
                WarehouseItem.sku == sku,
            )
        )
        return result.scalar_one_or_none()

    async def list_items(
        self,
        *,
        item_type: str | None = None,
        active_only: bool = False,
    ) -> list[WarehouseItem]:
        query = (
            select(WarehouseItem)
            .options(selectinload(WarehouseItem.stock_balances).selectinload(WarehouseStock.branch))
            .where(WarehouseItem.company_id == self.company_id)
            .order_by(WarehouseItem.name)
        )
        if item_type is not None:
            query = query.where(WarehouseItem.item_type == item_type)
        if active_only:
            query = query.where(WarehouseItem.is_active.is_(True))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_stock(self, item_id: UUID, branch_id: UUID | None) -> WarehouseStock | None:
        query = (
            select(WarehouseStock)
            .options(selectinload(WarehouseStock.branch))
            .where(
                WarehouseStock.company_id == self.company_id,
                WarehouseStock.item_id == item_id,
            )
        )
        if branch_id is None:
            query = query.where(WarehouseStock.branch_id.is_(None))
        else:
            query = query.where(WarehouseStock.branch_id == branch_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_stock_rows(
        self,
        *,
        item_type: str | None = None,
        branch_id: UUID | None = None,
    ) -> list[WarehouseStock]:
        query = (
            select(WarehouseStock)
            .join(WarehouseItem, WarehouseItem.id == WarehouseStock.item_id)
            .options(selectinload(WarehouseStock.item), selectinload(WarehouseStock.branch))
            .where(WarehouseStock.company_id == self.company_id)
            .order_by(WarehouseItem.name)
        )
        if item_type is not None:
            query = query.where(WarehouseItem.item_type == item_type)
        if branch_id is not None:
            query = query.where(WarehouseStock.branch_id == branch_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_movements(
        self,
        *,
        item_id: UUID | None = None,
        movement_type: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        limit: int = 100,
    ) -> list[WarehouseMovement]:
        query = (
            select(WarehouseMovement)
            .options(selectinload(WarehouseMovement.item))
            .where(WarehouseMovement.company_id == self.company_id)
            .order_by(WarehouseMovement.created_at.desc())
            .limit(min(limit, 500))
        )
        if item_id is not None:
            query = query.where(WarehouseMovement.item_id == item_id)
        if movement_type is not None:
            query = query.where(WarehouseMovement.movement_type == movement_type)
        if from_date is not None:
            query = query.where(
                WarehouseMovement.created_at >= datetime.combine(from_date, datetime.min.time(), tzinfo=UTC)
            )
        if to_date is not None:
            query = query.where(
                WarehouseMovement.created_at
                < datetime.combine(to_date + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
            )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_branch_name_map(self) -> dict[UUID, str]:
        result = await self.db.execute(
            select(Branch.id, Branch.name).where(Branch.company_id == self.company_id)
        )
        return {row[0]: row[1] for row in result.all()}
