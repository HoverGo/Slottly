"""company subscription offers and platform main admin role

Revision ID: 023
Revises: 022
Create Date: 2026-06-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_platform_main_admin", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.alter_column("users", "is_platform_main_admin", server_default=None)

    op.create_table(
        "company_subscription_offers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("price_monthly", sa.Integer(), nullable=False),
        sa.Column("max_users", sa.Integer(), nullable=False),
        sa.Column("max_branches", sa.Integer(), nullable=False),
        sa.Column("max_roles", sa.Integer(), nullable=False),
        sa.Column("max_services", sa.Integer(), nullable=False),
        sa.Column("max_appointments_per_month", sa.Integer(), nullable=False),
        sa.Column("base_plan_code", sa.String(length=50), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", name="uq_company_subscription_offer_company"),
    )
    op.create_index(
        "ix_company_subscription_offers_company_id",
        "company_subscription_offers",
        ["company_id"],
    )
    op.alter_column("company_subscription_offers", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_company_subscription_offers_company_id", table_name="company_subscription_offers")
    op.drop_table("company_subscription_offers")
    op.drop_column("users", "is_platform_main_admin")
