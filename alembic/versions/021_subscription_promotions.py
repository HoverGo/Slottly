"""subscription promotions for automatic checkout discounts

Revision ID: 021
Revises: 020
Create Date: 2026-06-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "subscription_promotions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("discount_percent", sa.Integer(), nullable=False),
        sa.Column("plan_codes", postgresql.JSONB(), nullable=True),
        sa.Column("actions", postgresql.JSONB(), nullable=True),
        sa.Column("for_all_companies", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("company_ids", postgresql.JSONB(), nullable=True),
        sa.Column("first_plan_purchase_only", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.alter_column("subscription_promotions", "for_all_companies", server_default=None)
    op.alter_column("subscription_promotions", "first_plan_purchase_only", server_default=None)
    op.alter_column("subscription_promotions", "used_count", server_default=None)
    op.alter_column("subscription_promotions", "is_active", server_default=None)

    op.add_column(
        "payments",
        sa.Column("subscription_promotion_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_payments_subscription_promotion_id",
        "payments",
        "subscription_promotions",
        ["subscription_promotion_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_payments_subscription_promotion_id", "payments", type_="foreignkey")
    op.drop_column("payments", "subscription_promotion_id")
    op.drop_table("subscription_promotions")
