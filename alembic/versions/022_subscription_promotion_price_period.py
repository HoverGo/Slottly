"""subscription promotion fixed price and period

Revision ID: 022
Revises: 021
Create Date: 2026-06-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "022"
down_revision: Union[str, None] = "021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("subscription_promotions", sa.Column("plan_code", sa.String(length=50), nullable=True))
    op.add_column("subscription_promotions", sa.Column("period_months", sa.Integer(), nullable=True))
    op.add_column("subscription_promotions", sa.Column("promotional_amount", sa.Integer(), nullable=True))
    op.add_column(
        "subscription_promotions",
        sa.Column("new_companies_only", sa.Boolean(), nullable=False, server_default="false"),
    )

    op.execute(
        """
        UPDATE subscription_promotions
        SET
            plan_code = COALESCE(plan_codes->>0, 'starter'),
            period_months = 1,
            promotional_amount = GREATEST(
                1,
                (
                    SELECT sp.price_monthly
                    FROM subscription_plans sp
                    WHERE sp.code = COALESCE(subscription_promotions.plan_codes->>0, 'starter')
                ) * (100 - discount_percent) / 100
            ),
            new_companies_only = first_plan_purchase_only
        """
    )

    op.alter_column("subscription_promotions", "plan_code", nullable=False)
    op.alter_column("subscription_promotions", "period_months", nullable=False)
    op.alter_column("subscription_promotions", "promotional_amount", nullable=False)
    op.alter_column("subscription_promotions", "new_companies_only", server_default=None)

    op.drop_column("subscription_promotions", "discount_percent")
    op.drop_column("subscription_promotions", "plan_codes")
    op.drop_column("subscription_promotions", "actions")
    op.drop_column("subscription_promotions", "first_plan_purchase_only")


def downgrade() -> None:
    op.add_column("subscription_promotions", sa.Column("discount_percent", sa.Integer(), nullable=True))
    op.add_column("subscription_promotions", sa.Column("plan_codes", sa.JSON(), nullable=True))
    op.add_column("subscription_promotions", sa.Column("actions", sa.JSON(), nullable=True))
    op.add_column(
        "subscription_promotions",
        sa.Column("first_plan_purchase_only", sa.Boolean(), nullable=False, server_default="false"),
    )

    op.execute(
        """
        UPDATE subscription_promotions sp
        SET
            discount_percent = GREATEST(
                1,
                100 - (sp.promotional_amount * 100 / NULLIF(
                    (SELECT p.price_monthly * sp.period_months FROM subscription_plans p WHERE p.code = sp.plan_code),
                    0
                ))
            ),
            plan_codes = jsonb_build_array(sp.plan_code),
            first_plan_purchase_only = sp.new_companies_only
        """
    )

    op.alter_column("subscription_promotions", "discount_percent", nullable=False)
    op.drop_column("subscription_promotions", "new_companies_only")
    op.drop_column("subscription_promotions", "promotional_amount")
    op.drop_column("subscription_promotions", "period_months")
    op.drop_column("subscription_promotions", "plan_code")
