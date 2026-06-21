"""public online booking slug and nullable appointment creator

Revision ID: 018
Revises: 017
Create Date: 2026-06-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("booking_slug", sa.String(64), nullable=True))
    op.add_column(
        "companies",
        sa.Column("public_booking_enabled", sa.Boolean(), server_default="false", nullable=False),
    )
    op.create_index("ix_companies_booking_slug", "companies", ["booking_slug"], unique=True)
    op.alter_column("companies", "public_booking_enabled", server_default=None)

    op.alter_column(
        "member_appointments",
        "created_by_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "member_appointments",
        "created_by_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_index("ix_companies_booking_slug", "companies")
    op.drop_column("companies", "public_booking_enabled")
    op.drop_column("companies", "booking_slug")
