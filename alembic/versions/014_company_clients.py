"""company clients and appointment client fields

Revision ID: 014
Revises: 013
Create Date: 2026-06-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "company_clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("phone_normalized", sa.String(20), nullable=False),
        sa.Column("phone_display", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("company_id", "phone_normalized", name="uq_company_client_phone"),
    )
    op.create_index("ix_company_clients_company_id", "company_clients", ["company_id"])
    op.create_index("ix_company_clients_phone_normalized", "company_clients", ["phone_normalized"])

    op.add_column(
        "member_appointments",
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company_clients.id"), nullable=True),
    )
    op.add_column("member_appointments", sa.Column("client_full_name", sa.String(255), nullable=True))
    op.add_column("member_appointments", sa.Column("client_email", sa.String(255), nullable=True))
    op.alter_column(
        "member_appointments",
        "note",
        existing_type=sa.String(500),
        type_=sa.Text(),
        existing_nullable=True,
    )
    op.create_index("ix_member_appointments_client_id", "member_appointments", ["client_id"])


def downgrade() -> None:
    op.drop_index("ix_member_appointments_client_id", "member_appointments")
    op.drop_column("member_appointments", "client_email")
    op.drop_column("member_appointments", "client_full_name")
    op.drop_column("member_appointments", "client_id")
    op.alter_column(
        "member_appointments",
        "note",
        existing_type=sa.Text(),
        type_=sa.String(500),
        existing_nullable=True,
    )
    op.drop_table("company_clients")
