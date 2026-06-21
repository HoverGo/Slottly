"""schedule exception date ranges and multiple dates

Revision ID: 008
Revises: 007
Create Date: 2026-06-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "member_schedule_exceptions",
        sa.Column("exception_date_to", sa.Date(), nullable=True),
    )
    op.add_column(
        "member_schedule_exceptions",
        sa.Column("exception_dates", postgresql.JSONB(), nullable=True),
    )
    op.execute(
        """
        UPDATE member_schedule_exceptions
        SET exception_date_to = exception_date
        WHERE exception_date_to IS NULL
        """
    )
    op.execute("DROP INDEX IF EXISTS uq_member_schedule_exception_day_off")


def downgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX uq_member_schedule_exception_day_off
        ON member_schedule_exceptions (company_id, member_id, exception_date)
        WHERE kind = 'day_off'
        """
    )
    op.drop_column("member_schedule_exceptions", "exception_dates")
    op.drop_column("member_schedule_exceptions", "exception_date_to")
