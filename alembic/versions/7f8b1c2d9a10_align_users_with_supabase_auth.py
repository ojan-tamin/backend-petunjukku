"""legacy supabase alignment no-op

Revision ID: 7f8b1c2d9a10
Revises: 28d77849332c
Create Date: 2026-04-18 10:30:00.000000
"""

from typing import Sequence, Union

revision: str = "7f8b1c2d9a10"
down_revision: Union[str, Sequence[str], None] = "28d77849332c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
