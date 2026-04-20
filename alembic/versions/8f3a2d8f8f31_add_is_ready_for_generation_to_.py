"""add is_ready_for_generation to planning_states

Revision ID: 8f3a2d8f8f31
Revises: 28d77849332c
Create Date: 2026-04-20 22:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f3a2d8f8f31"
down_revision: Union[str, Sequence[str], None] = "28d77849332c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("planning_states") as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_ready_for_generation",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("planning_states") as batch_op:
        batch_op.drop_column("is_ready_for_generation")
