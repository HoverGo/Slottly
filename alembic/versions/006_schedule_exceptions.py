"""member schedule exceptions day off and slot blocks

Revision ID: 006
Revises: 005
Create Date: 2026-06-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE schedule_exception_kind AS ENUM ('day_off', 'slot_block');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    exception_kind = postgresql.ENUM(
        "day_off", "slot_block", name="schedule_exception_kind", create_type=False
    )

    op.create_table(
        "member_schedule_exceptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("exception_date", sa.Date(), nullable=False),
        sa.Column("kind", exception_kind, nullable=False),
        sa.Column("block_config", postgresql.JSONB(), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["member_id"], ["company_members.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_member_schedule_exceptions_company_id", "member_schedule_exceptions", ["company_id"]
    )
    op.create_index(
        "ix_member_schedule_exceptions_member_id", "member_schedule_exceptions", ["member_id"]
    )
    op.create_index(
        "ix_member_schedule_exceptions_date", "member_schedule_exceptions", ["exception_date"]
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_member_schedule_exception_day_off
        ON member_schedule_exceptions (company_id, member_id, exception_date)
        WHERE kind = 'day_off'
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_member_schedule_exception_day_off")
    op.drop_index("ix_member_schedule_exceptions_date", "member_schedule_exceptions")
    op.drop_index("ix_member_schedule_exceptions_member_id", "member_schedule_exceptions")
    op.drop_index("ix_member_schedule_exceptions_company_id", "member_schedule_exceptions")
    op.drop_table("member_schedule_exceptions")
    op.execute("DROP TYPE IF EXISTS schedule_exception_kind")
