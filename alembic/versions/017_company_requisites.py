"""company billing requisites

Revision ID: 017
Revises: 016
Create Date: 2026-06-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "company_requisites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("legal_name", sa.String(255), nullable=False),
        sa.Column("inn", sa.String(12), nullable=False),
        sa.Column("kpp", sa.String(9), nullable=True),
        sa.Column("billing_email", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("company_id", name="uq_company_requisites_company_id"),
    )
    op.create_index("ix_company_requisites_company_id", "company_requisites", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_company_requisites_company_id", "company_requisites")
    op.drop_table("company_requisites")
