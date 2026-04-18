"""align users with supabase auth

Revision ID: 7f8b1c2d9a10
Revises: 28d77849332c
Create Date: 2026-04-18 10:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7f8b1c2d9a10"
down_revision: Union[str, Sequence[str], None] = "28d77849332c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("users", "password_hash")
    op.create_foreign_key(
        "fk_users_auth_users_id",
        "users",
        "users",
        ["id"],
        ["id"],
        referent_schema="auth",
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_auth_users_id", "users", type_="foreignkey")
    op.add_column("users", sa.Column("password_hash", sa.Text(), nullable=True))
