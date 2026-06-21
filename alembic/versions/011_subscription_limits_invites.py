"""subscription limits, employee invites and compensation

Revision ID: 011
Revises: 010
Create Date: 2026-06-17

"""

from typing import Sequence, Union
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "subscription_plans",
        sa.Column("max_services", sa.Integer(), nullable=False, server_default="10"),
    )
    op.add_column(
        "subscription_plans",
        sa.Column("max_appointments_per_month", sa.Integer(), nullable=False, server_default="100"),
    )
    op.alter_column("subscription_plans", "max_services", server_default=None)
    op.alter_column("subscription_plans", "max_appointments_per_month", server_default=None)

    op.execute(
        """
        UPDATE subscription_plans SET max_services = 5, max_appointments_per_month = 50
        WHERE code NOT IN ('starter', 'business', 'enterprise', 'basic')
        """
    )
    op.execute(
        "UPDATE subscription_plans SET max_services = 20, max_appointments_per_month = 500 WHERE code = 'starter'"
    )
    op.execute(
        "UPDATE subscription_plans SET max_services = 100, max_appointments_per_month = 3000 WHERE code = 'business'"
    )
    op.execute(
        "UPDATE subscription_plans SET max_services = 500, max_appointments_per_month = 20000 WHERE code = 'enterprise'"
    )

    op.execute(
        f"""
        INSERT INTO subscription_plans (
            id, code, name, description,
            max_users, max_branches, max_roles, max_services, max_appointments_per_month,
            price_monthly, sort_order
        )
        SELECT
            '{uuid.uuid4()}', 'basic', 'Базовый',
            'Бесплатный тариф: до 3 сотрудников, 5 услуг, 50 записей в месяц',
            3, 1, 3, 5, 50, 0, 0
        WHERE NOT EXISTS (SELECT 1 FROM subscription_plans WHERE code = 'basic')
        """
    )

    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE compensation_type AS ENUM ('percent', 'salary', 'salary_plus_percent');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    compensation_type = postgresql.ENUM(
        "percent",
        "salary",
        "salary_plus_percent",
        name="compensation_type",
        create_type=False,
    )

    op.execute("ALTER TYPE join_request_status ADD VALUE IF NOT EXISTS 'pending_activation'")

    op.add_column(
        "company_members",
        sa.Column("compensation_type", compensation_type, nullable=True),
    )
    op.add_column("company_members", sa.Column("compensation_rate", sa.Integer(), nullable=True))
    op.add_column("company_members", sa.Column("compensation_percent", sa.Integer(), nullable=True))

    op.alter_column("company_join_requests", "user_id", existing_type=postgresql.UUID(), nullable=True)
    op.add_column("company_join_requests", sa.Column("invite_email", sa.String(255), nullable=True))
    op.add_column("company_join_requests", sa.Column("invite_full_name", sa.String(255), nullable=True))
    op.add_column("company_join_requests", sa.Column("invite_phone", sa.String(50), nullable=True))
    op.add_column("company_join_requests", sa.Column("activation_token", sa.String(64), nullable=True))
    op.add_column(
        "company_join_requests",
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "company_join_requests",
        sa.Column("compensation_type", compensation_type, nullable=True),
    )
    op.add_column("company_join_requests", sa.Column("compensation_rate", sa.Integer(), nullable=True))
    op.add_column("company_join_requests", sa.Column("compensation_percent", sa.Integer(), nullable=True))
    op.create_index(
        "ix_company_join_requests_activation_token",
        "company_join_requests",
        ["activation_token"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_company_join_requests_activation_token", "company_join_requests")
    op.drop_column("company_join_requests", "compensation_percent")
    op.drop_column("company_join_requests", "compensation_rate")
    op.drop_column("company_join_requests", "compensation_type")
    op.drop_column("company_join_requests", "token_expires_at")
    op.drop_column("company_join_requests", "activation_token")
    op.drop_column("company_join_requests", "invite_phone")
    op.drop_column("company_join_requests", "invite_full_name")
    op.drop_column("company_join_requests", "invite_email")
    op.alter_column("company_join_requests", "user_id", existing_type=postgresql.UUID(), nullable=False)

    op.drop_column("company_members", "compensation_percent")
    op.drop_column("company_members", "compensation_rate")
    op.drop_column("company_members", "compensation_type")

    op.drop_column("subscription_plans", "max_appointments_per_month")
    op.drop_column("subscription_plans", "max_services")
    op.execute("DELETE FROM subscription_plans WHERE code = 'basic'")
    op.execute("DROP TYPE IF EXISTS compensation_type")
