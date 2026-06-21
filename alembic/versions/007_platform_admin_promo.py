"""platform admin and promo codes

Revision ID: 007
Revises: 006
Create Date: 2026-06-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_platform_admin", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.alter_column("users", "is_platform_admin", server_default=None)

    op.create_table(
        "promo_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("discount_percent", sa.Integer(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("plan_codes", postgresql.JSONB(), nullable=True),
        sa.Column("actions", postgresql.JSONB(), nullable=True),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_promo_codes_user_id", "promo_codes", ["user_id"])

    op.add_column("payments", sa.Column("promo_code_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("payments", sa.Column("original_amount", sa.Integer(), nullable=True))
    op.add_column("payments", sa.Column("discount_amount", sa.Integer(), nullable=False, server_default="0"))
    op.alter_column("payments", "discount_amount", server_default=None)
    op.create_foreign_key(
        "fk_payments_promo_code_id", "payments", "promo_codes", ["promo_code_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_payments_promo_code_id", "payments", type_="foreignkey")
    op.drop_column("payments", "discount_amount")
    op.drop_column("payments", "original_amount")
    op.drop_column("payments", "promo_code_id")
    op.drop_index("ix_promo_codes_user_id", "promo_codes")
    op.drop_table("promo_codes")
    op.drop_column("users", "is_platform_admin")
