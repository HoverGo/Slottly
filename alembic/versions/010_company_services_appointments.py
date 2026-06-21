"""company services and member appointments

Revision ID: 010
Revises: 009
Create Date: 2026-06-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE appointment_status AS ENUM ('scheduled', 'cancelled', 'completed');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    appointment_status = postgresql.ENUM(
        "scheduled",
        "cancelled",
        "completed",
        name="appointment_status",
        create_type=False,
    )

    op.create_table(
        "company_services",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=True),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company_members.id"), nullable=True),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("branches.id"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("company_id", "id", name="uq_company_service_tenant"),
    )
    op.create_index("ix_company_services_company_id", "company_services", ["company_id"])
    op.create_index("ix_company_services_member_id", "company_services", ["member_id"])
    op.alter_column("company_services", "is_active", server_default=None)

    op.create_table(
        "member_appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company_members.id"), nullable=False),
        sa.Column(
            "service_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("company_services.id"),
            nullable=False,
        ),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("client_name", sa.String(255), nullable=True),
        sa.Column("client_phone", sa.String(50), nullable=True),
        sa.Column("status", appointment_status, nullable=False, server_default="scheduled"),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_member_appointments_company_id", "member_appointments", ["company_id"])
    op.create_index("ix_member_appointments_member_id", "member_appointments", ["member_id"])
    op.create_index("ix_member_appointments_starts_at", "member_appointments", ["starts_at"])
    op.alter_column("member_appointments", "status", server_default=None)


def downgrade() -> None:
    op.drop_table("member_appointments")
    op.drop_table("company_services")
    op.execute("DROP TYPE IF EXISTS appointment_status")
