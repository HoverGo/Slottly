"""service buffers and category

Revision ID: 015
Revises: 014
Create Date: 2026-06-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("company_services", sa.Column("category", sa.String(100), nullable=True))
    op.add_column(
        "company_services",
        sa.Column("buffer_before_minutes", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "company_services",
        sa.Column("buffer_after_minutes", sa.Integer(), server_default="0", nullable=False),
    )
    op.alter_column("company_services", "buffer_before_minutes", server_default=None)
    op.alter_column("company_services", "buffer_after_minutes", server_default=None)

    op.add_column(
        "member_appointments",
        sa.Column("buffer_before_minutes", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "member_appointments",
        sa.Column("buffer_after_minutes", sa.Integer(), server_default="0", nullable=False),
    )
    op.alter_column("member_appointments", "buffer_before_minutes", server_default=None)
    op.alter_column("member_appointments", "buffer_after_minutes", server_default=None)


def downgrade() -> None:
    op.drop_column("member_appointments", "buffer_after_minutes")
    op.drop_column("member_appointments", "buffer_before_minutes")
    op.drop_column("company_services", "buffer_after_minutes")
    op.drop_column("company_services", "buffer_before_minutes")
    op.drop_column("company_services", "category")
