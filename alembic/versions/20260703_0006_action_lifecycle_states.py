"""add action lifecycle states

Revision ID: 20260703_0006
Revises: 20260701_0005
Create Date: 2026-07-03 20:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260703_0006"
down_revision: Union[str, None] = "20260701_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "action_lifecycle_states",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("entity_kind", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("converted_follow_up_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "entity_kind", "entity_id", name="uq_action_lifecycle_user_kind_entity"),
    )
    op.create_index(op.f("ix_action_lifecycle_states_id"), "action_lifecycle_states", ["id"], unique=False)
    op.create_index(op.f("ix_action_lifecycle_states_user_id"), "action_lifecycle_states", ["user_id"], unique=False)
    op.create_index(op.f("ix_action_lifecycle_states_entity_kind"), "action_lifecycle_states", ["entity_kind"], unique=False)
    op.create_index(op.f("ix_action_lifecycle_states_entity_id"), "action_lifecycle_states", ["entity_id"], unique=False)
    op.create_index(op.f("ix_action_lifecycle_states_entity_type"), "action_lifecycle_states", ["entity_type"], unique=False)
    op.create_index(op.f("ix_action_lifecycle_states_status"), "action_lifecycle_states", ["status"], unique=False)
    op.create_index(op.f("ix_action_lifecycle_states_converted_follow_up_id"), "action_lifecycle_states", ["converted_follow_up_id"], unique=False)
    op.create_index(op.f("ix_action_lifecycle_states_first_seen_at"), "action_lifecycle_states", ["first_seen_at"], unique=False)
    op.create_index(op.f("ix_action_lifecycle_states_last_seen_at"), "action_lifecycle_states", ["last_seen_at"], unique=False)
    op.create_index(op.f("ix_action_lifecycle_states_created_at"), "action_lifecycle_states", ["created_at"], unique=False)
    op.create_index(
        "ix_action_lifecycle_states_user_kind_status",
        "action_lifecycle_states",
        ["user_id", "entity_kind", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_action_lifecycle_states_user_kind_status", table_name="action_lifecycle_states")
    op.drop_index(op.f("ix_action_lifecycle_states_created_at"), table_name="action_lifecycle_states")
    op.drop_index(op.f("ix_action_lifecycle_states_last_seen_at"), table_name="action_lifecycle_states")
    op.drop_index(op.f("ix_action_lifecycle_states_first_seen_at"), table_name="action_lifecycle_states")
    op.drop_index(op.f("ix_action_lifecycle_states_converted_follow_up_id"), table_name="action_lifecycle_states")
    op.drop_index(op.f("ix_action_lifecycle_states_status"), table_name="action_lifecycle_states")
    op.drop_index(op.f("ix_action_lifecycle_states_entity_type"), table_name="action_lifecycle_states")
    op.drop_index(op.f("ix_action_lifecycle_states_entity_id"), table_name="action_lifecycle_states")
    op.drop_index(op.f("ix_action_lifecycle_states_entity_kind"), table_name="action_lifecycle_states")
    op.drop_index(op.f("ix_action_lifecycle_states_user_id"), table_name="action_lifecycle_states")
    op.drop_index(op.f("ix_action_lifecycle_states_id"), table_name="action_lifecycle_states")
    op.drop_table("action_lifecycle_states")
