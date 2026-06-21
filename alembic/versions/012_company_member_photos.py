"""company and member photos

Revision ID: 012
Revises: 011
Create Date: 2026-06-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("photo_path", sa.String(512), nullable=True))
    op.add_column("company_members", sa.Column("photo_path", sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column("company_members", "photo_path")
    op.drop_column("companies", "photo_path")
