"""unified subscription billing model

Revision ID: 004
Revises: 003
Create Date: 2026-06-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE payment_action AS ENUM ('purchase', 'renew', 'change_plan');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    payment_action = postgresql.ENUM(
        "purchase", "renew", "change_plan", name="payment_action", create_type=False
    )

    op.add_column("user_subscriptions", sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("user_subscriptions", sa.Column("scheduled_plan_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column(
        "user_subscriptions", sa.Column("scheduled_change_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_foreign_key(
        "fk_user_subscriptions_company_id", "user_subscriptions", "companies", ["company_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_user_subscriptions_scheduled_plan_id",
        "user_subscriptions",
        "subscription_plans",
        ["scheduled_plan_id"],
        ["id"],
    )
    op.create_index("ix_user_subscriptions_company_id", "user_subscriptions", ["company_id"], unique=True)

    op.add_column("payments", sa.Column("user_subscription_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("payments", sa.Column("action", payment_action, nullable=True))
    op.add_column("payments", sa.Column("period_months", sa.Integer(), nullable=True))
    op.execute("UPDATE payments SET action = 'purchase', period_months = 1 WHERE action IS NULL")
    op.alter_column("payments", "action", nullable=False)
    op.alter_column("payments", "period_months", nullable=False)
    op.create_foreign_key(
        "fk_payments_user_subscription_id",
        "payments",
        "user_subscriptions",
        ["user_subscription_id"],
        ["id"],
    )

    op.drop_constraint("payments_company_id_fkey", "payments", type_="foreignkey")
    op.drop_column("payments", "company_id")
    op.drop_column("payments", "target")

    op.drop_column("subscription_plans", "plan_type")
    op.drop_column("subscription_plans", "allows_company_creation")
    op.drop_column("subscription_plans", "is_minimum_for_new_company")

    op.drop_index("ix_company_subscriptions_company_id", table_name="company_subscriptions")
    op.drop_table("company_subscriptions")

    op.execute("DROP TYPE IF EXISTS plan_type")
    op.execute("DROP TYPE IF EXISTS subscription_target")


def downgrade() -> None:
    raise NotImplementedError("Откат миграции 004 не поддерживается")
