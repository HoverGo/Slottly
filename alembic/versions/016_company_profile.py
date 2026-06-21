"""company profile fields and gallery photos

Revision ID: 016
Revises: 015
Create Date: 2026-06-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

organization_type = postgresql.ENUM("ip", "self_employed", "llc", name="organization_type", create_type=False)


def upgrade() -> None:
    organization_type.create(op.get_bind(), checkfirst=True)

    op.add_column("companies", sa.Column("country", sa.String(100), nullable=True))
    op.add_column("companies", sa.Column("city", sa.String(100), nullable=True))
    op.add_column("companies", sa.Column("address", sa.String(500), nullable=True))
    op.add_column("companies", sa.Column("phone", sa.String(50), nullable=True))
    op.add_column("companies", sa.Column("organization_type", organization_type, nullable=True))
    op.add_column("companies", sa.Column("working_hours", postgresql.JSONB(), nullable=True))
    op.add_column(
        "companies",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "company_gallery_photos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("path", sa.String(512), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_company_gallery_photos_company_id", "company_gallery_photos", ["company_id"])
    op.alter_column("company_gallery_photos", "sort_order", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_company_gallery_photos_company_id", "company_gallery_photos")
    op.drop_table("company_gallery_photos")
    op.drop_column("companies", "updated_at")
    op.drop_column("companies", "working_hours")
    op.drop_column("companies", "organization_type")
    op.drop_column("companies", "phone")
    op.drop_column("companies", "address")
    op.drop_column("companies", "city")
    op.drop_column("companies", "country")
    organization_type.drop(op.get_bind(), checkfirst=True)
