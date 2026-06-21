from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

WarehouseItemTypeLiteral = Literal["product", "consumable"]
StockMovementTypeLiteral = Literal["receipt", "issue", "adjustment", "transfer"]


class WarehouseItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    item_type: WarehouseItemTypeLiteral
    sku: str | None = Field(default=None, max_length=64)
    unit: str = Field(default="шт", max_length=20)
    description: str | None = Field(default=None, max_length=2000)
    min_quantity: int | None = Field(default=None, ge=0)
    initial_quantity: int | None = Field(default=None, ge=0, description="Начальный остаток на основном складе")
    branch_id: UUID | None = Field(default=None, description="Филиал для начального остатка")


class WarehouseItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    sku: str | None = Field(default=None, max_length=64)
    unit: str | None = Field(default=None, max_length=20)
    description: str | None = Field(default=None, max_length=2000)
    min_quantity: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    clear_sku: bool = False
    clear_min_quantity: bool = False


class WarehouseStockBalanceResponse(BaseModel):
    branch_id: UUID | None
    branch_name: str | None
    quantity: int


class WarehouseItemResponse(BaseModel):
    id: UUID
    company_id: UUID
    item_type: WarehouseItemTypeLiteral
    name: str
    sku: str | None
    unit: str
    description: str | None
    min_quantity: int | None
    is_active: bool
    total_quantity: int
    stock: list[WarehouseStockBalanceResponse]
    is_low_stock: bool
    created_by_id: UUID
    created_at: Any
    updated_at: Any


class StockMovementCreate(BaseModel):
    item_id: UUID
    movement_type: StockMovementTypeLiteral
    quantity: int | None = Field(default=None, gt=0, description="Количество для прихода, расхода, перемещения")
    quantity_delta: int | None = Field(
        default=None, description="Изменение для корректировки (может быть отрицательным)"
    )
    branch_id: UUID | None = Field(default=None, description="Склад/филиал для прихода, расхода, корректировки")
    from_branch_id: UUID | None = None
    to_branch_id: UUID | None = None
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_movement(self) -> "StockMovementCreate":
        if self.movement_type in ("receipt", "issue", "transfer"):
            if self.quantity is None:
                raise ValueError("Укажите quantity")
        if self.movement_type == "adjustment":
            if self.quantity_delta is None or self.quantity_delta == 0:
                raise ValueError("Укажите quantity_delta для корректировки")
        if self.movement_type == "transfer":
            if self.from_branch_id is None or self.to_branch_id is None:
                raise ValueError("Для перемещения укажите from_branch_id и to_branch_id")
            if self.from_branch_id == self.to_branch_id:
                raise ValueError("Филиалы перемещения должны отличаться")
        return self


class StockMovementResponse(BaseModel):
    id: UUID
    company_id: UUID
    item_id: UUID
    item_name: str
    item_type: WarehouseItemTypeLiteral
    movement_type: StockMovementTypeLiteral
    quantity: int
    branch_id: UUID | None
    branch_name: str | None
    from_branch_id: UUID | None
    from_branch_name: str | None
    to_branch_id: UUID | None
    to_branch_name: str | None
    quantity_before: int | None
    quantity_after: int | None
    note: str | None
    created_by_id: UUID
    created_at: Any


class WarehouseStockRowResponse(BaseModel):
    item_id: UUID
    item_name: str
    item_type: WarehouseItemTypeLiteral
    sku: str | None
    unit: str
    branch_id: UUID | None
    branch_name: str | None
    quantity: int
    min_quantity: int | None
    is_low_stock: bool
