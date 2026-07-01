"""add recommendation identity column

Revision ID: 20260701_0004
Revises: 20260701_0003
Create Date: 2026-07-01 22:25:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260701_0004"
down_revision: Union[str, None] = "20260701_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("recommendation_impressions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("recommendation_id", sa.String(length=128), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_recommendation_impressions_recommendation_id"),
            ["recommendation_id"],
            unique=False,
        )

    op.execute(
        """
        UPDATE recommendation_impressions
        SET recommendation_id = recommendation_type
        WHERE recommendation_id IS NULL
        """
    )

    with op.batch_alter_table("recommendation_impressions", schema=None) as batch_op:
        batch_op.alter_column("recommendation_id", existing_type=sa.String(length=128), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("recommendation_impressions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_recommendation_impressions_recommendation_id"))
        batch_op.drop_column("recommendation_id")
