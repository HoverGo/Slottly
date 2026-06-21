"""roles permissions and work schedules

Revision ID: 005
Revises: 004
Create Date: 2026-06-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "company_roles",
        sa.Column("permissions", postgresql.JSONB(), nullable=False, server_default="[]"),
    )
    op.alter_column("company_roles", "permissions", server_default=None)

    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE schedule_pattern_type AS ENUM ('weekly', 'cycle', 'manual');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    schedule_pattern = postgresql.ENUM(
        "weekly", "cycle", "manual", name="schedule_pattern_type", create_type=False
    )

    op.create_table(
        "member_work_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("time_start", sa.Time(), nullable=False),
        sa.Column("time_end", sa.Time(), nullable=False),
        sa.Column("slot_interval_minutes", sa.Integer(), nullable=False),
        sa.Column("pattern_type", schedule_pattern, nullable=False),
        sa.Column("pattern_config", postgresql.JSONB(), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["member_id"], ["company_members.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_member_work_schedules_company_id", "member_work_schedules", ["company_id"])
    op.create_index("ix_member_work_schedules_member_id", "member_work_schedules", ["member_id"])


def downgrade() -> None:
    op.drop_index("ix_member_work_schedules_member_id", "member_work_schedules")
    op.drop_index("ix_member_work_schedules_company_id", "member_work_schedules")
    op.drop_table("member_work_schedules")
    op.drop_column("company_roles", "permissions")
    op.execute("DROP TYPE IF EXISTS schedule_pattern_type")
