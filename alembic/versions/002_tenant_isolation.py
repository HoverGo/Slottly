"""tenant isolation constraints

Revision ID: 002
Revises: 001
Create Date: 2026-06-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint("uq_company_role_tenant", "company_roles", ["company_id", "id"])
    op.create_unique_constraint("uq_branch_tenant", "branches", ["company_id", "id"])

    op.create_index("ix_company_roles_company_id", "company_roles", ["company_id"])
    op.create_index("ix_company_members_company_id", "company_members", ["company_id"])
    op.create_index("ix_branches_company_id", "branches", ["company_id"])
    op.create_index("ix_company_subscriptions_company_id", "company_subscriptions", ["company_id"])

    op.drop_constraint("company_members_role_id_fkey", "company_members", type_="foreignkey")
    op.create_foreign_key(
        "fk_member_role_same_tenant",
        "company_members",
        "company_roles",
        ["company_id", "role_id"],
        ["company_id", "id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_member_role_same_tenant", "company_members", type_="foreignkey")
    op.create_foreign_key(
        "company_members_role_id_fkey",
        "company_members",
        "company_roles",
        ["role_id"],
        ["id"],
    )

    op.drop_index("ix_company_subscriptions_company_id", "company_subscriptions")
    op.drop_index("ix_branches_company_id", "branches")
    op.drop_index("ix_company_members_company_id", "company_members")
    op.drop_index("ix_company_roles_company_id", "company_roles")

    op.drop_constraint("uq_branch_tenant", "branches", type_="unique")
    op.drop_constraint("uq_company_role_tenant", "company_roles", type_="unique")
