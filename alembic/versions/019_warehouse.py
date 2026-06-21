"""warehouse items stock and movements

Revision ID: 019
Revises: 018
Create Date: 2026-06-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

warehouse_item_type = postgresql.ENUM(
    "product", "consumable", name="warehouse_item_type", create_type=False
)
stock_movement_type = postgresql.ENUM(
    "receipt", "issue", "adjustment", "transfer", name="stock_movement_type", create_type=False
)


def upgrade() -> None:
    warehouse_item_type.create(op.get_bind(), checkfirst=True)
    stock_movement_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "warehouse_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("item_type", warehouse_item_type, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sku", sa.String(64), nullable=True),
        sa.Column("unit", sa.String(20), server_default="шт", nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("min_quantity", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("company_id", "id", name="uq_warehouse_item_tenant"),
        sa.UniqueConstraint("company_id", "sku", name="uq_warehouse_item_sku"),
    )
    op.create_index("ix_warehouse_items_company_id", "warehouse_items", ["company_id"])
    op.create_index("ix_warehouse_items_item_type", "warehouse_items", ["item_type"])
    op.alter_column("warehouse_items", "unit", server_default=None)
    op.alter_column("warehouse_items", "is_active", server_default=None)

    op.create_table(
        "warehouse_stock",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouse_items.id"), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("branches.id"), nullable=True),
        sa.Column("quantity", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("company_id", "item_id", "branch_id", name="uq_warehouse_stock_location"),
    )
    op.create_index("ix_warehouse_stock_company_id", "warehouse_stock", ["company_id"])
    op.create_index("ix_warehouse_stock_item_id", "warehouse_stock", ["item_id"])
    op.alter_column("warehouse_stock", "quantity", server_default=None)

    op.create_table(
        "warehouse_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouse_items.id"), nullable=False),
        sa.Column("movement_type", stock_movement_type, nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("branches.id"), nullable=True),
        sa.Column("from_branch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("branches.id"), nullable=True),
        sa.Column("to_branch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("branches.id"), nullable=True),
        sa.Column("quantity_before", sa.Integer(), nullable=True),
        sa.Column("quantity_after", sa.Integer(), nullable=True),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_warehouse_movements_company_id", "warehouse_movements", ["company_id"])
    op.create_index("ix_warehouse_movements_item_id", "warehouse_movements", ["item_id"])
    op.create_index("ix_warehouse_movements_created_at", "warehouse_movements", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_warehouse_movements_created_at", "warehouse_movements")
    op.drop_index("ix_warehouse_movements_item_id", "warehouse_movements")
    op.drop_index("ix_warehouse_movements_company_id", "warehouse_movements")
    op.drop_table("warehouse_movements")
    op.drop_index("ix_warehouse_stock_item_id", "warehouse_stock")
    op.drop_index("ix_warehouse_stock_company_id", "warehouse_stock")
    op.drop_table("warehouse_stock")
    op.drop_index("ix_warehouse_items_item_type", "warehouse_items")
    op.drop_index("ix_warehouse_items_company_id", "warehouse_items")
    op.drop_table("warehouse_items")
    stock_movement_type.drop(op.get_bind(), checkfirst=True)
    warehouse_item_type.drop(op.get_bind(), checkfirst=True)
