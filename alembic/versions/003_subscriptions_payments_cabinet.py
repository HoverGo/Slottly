"""subscriptions payments cabinet foundation

Revision ID: 003
Revises: 002
Create Date: 2026-06-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ensure_enum(name: str, values: tuple[str, ...]) -> postgresql.ENUM:
    labels = ", ".join(f"'{v}'" for v in values)
    op.execute(
        f"""
        DO $$ BEGIN
            CREATE TYPE {name} AS ENUM ({labels});
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    return postgresql.ENUM(*values, name=name, create_type=False)


def upgrade() -> None:
    plan_type = _ensure_enum("plan_type", ("user", "company"))

    op.add_column(
        "subscription_plans",
        sa.Column("plan_type", plan_type, nullable=False, server_default="company"),
    )
    op.add_column(
        "subscription_plans",
        sa.Column("allows_company_creation", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.alter_column("subscription_plans", "plan_type", server_default=None)

    payment_provider = _ensure_enum("payment_provider", ("mock", "yookassa", "cloudpayments"))
    payment_status = _ensure_enum(
        "payment_status", ("pending", "succeeded", "failed", "cancelled", "refunded")
    )
    subscription_target = _ensure_enum("subscription_target", ("user", "company"))
    join_request_status = _ensure_enum(
        "join_request_status", ("pending", "accepted", "rejected", "cancelled")
    )

    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target", subscription_target, nullable=False),
        sa.Column("provider", payment_provider, nullable=False),
        sa.Column("provider_payment_id", sa.String(length=255), nullable=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", payment_status, nullable=False),
        sa.Column("confirmation_url", sa.String(length=1024), nullable=True),
        sa.Column("provider_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payments_user_id", "payments", ["user_id"])

    op.create_table(
        "user_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "active", "expired", "cancelled", name="subscription_status", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"]),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_subscriptions_user_id", "user_subscriptions", ["user_id"])

    op.add_column(
        "company_subscriptions",
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_company_subscriptions_payment_id",
        "company_subscriptions",
        "payments",
        ["payment_id"],
        ["id"],
    )

    op.create_table(
        "company_join_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invited_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", join_request_status, nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["invited_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_join_requests_user_id", "company_join_requests", ["user_id"])
    op.create_index("ix_join_requests_company_id", "company_join_requests", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_join_requests_company_id", "company_join_requests")
    op.drop_index("ix_join_requests_user_id", "company_join_requests")
    op.drop_table("company_join_requests")

    op.drop_constraint("fk_company_subscriptions_payment_id", "company_subscriptions", type_="foreignkey")
    op.drop_column("company_subscriptions", "payment_id")

    op.drop_index("ix_user_subscriptions_user_id", "user_subscriptions")
    op.drop_table("user_subscriptions")

    op.drop_index("ix_payments_user_id", "payments")
    op.drop_table("payments")

    op.drop_column("subscription_plans", "allows_company_creation")
    op.drop_column("subscription_plans", "plan_type")

    op.execute("DROP TYPE IF EXISTS join_request_status")
    op.execute("DROP TYPE IF EXISTS subscription_target")
    op.execute("DROP TYPE IF EXISTS payment_status")
    op.execute("DROP TYPE IF EXISTS payment_provider")
    op.execute("DROP TYPE IF EXISTS plan_type")
