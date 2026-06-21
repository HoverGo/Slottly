"""company client reviews and ratings

Revision ID: 020
Revises: 019
Create Date: 2026-06-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "company_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company_clients.id"), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company_members.id"), nullable=True),
        sa.Column("client_display_name", sa.String(255), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("is_visible", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_company_reviews_company_id", "company_reviews", ["company_id"])
    op.create_index("ix_company_reviews_member_id", "company_reviews", ["member_id"])
    op.create_index("ix_company_reviews_created_at", "company_reviews", ["created_at"])
    op.alter_column("company_reviews", "is_visible", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_company_reviews_created_at", "company_reviews")
    op.drop_index("ix_company_reviews_member_id", "company_reviews")
    op.drop_index("ix_company_reviews_company_id", "company_reviews")
    op.drop_table("company_reviews")
