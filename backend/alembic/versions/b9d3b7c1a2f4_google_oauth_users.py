"""google_oauth_users

Revision ID: b9d3b7c1a2f4
Revises: 63299f57d02f
Create Date: 2026-04-13 12:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b9d3b7c1a2f4"
down_revision: Union[str, Sequence[str], None] = "63299f57d02f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("google_sub", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("name", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.String(length=500), nullable=True))

    op.execute("UPDATE users SET google_sub = email WHERE google_sub IS NULL")

    op.alter_column("users", "google_sub", existing_type=sa.String(length=255), nullable=False)
    op.create_index(op.f("ix_users_google_sub"), "users", ["google_sub"], unique=True)

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("hashed_password")


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("hashed_password", sa.String(length=255), nullable=True))

    op.drop_index(op.f("ix_users_google_sub"), table_name="users")
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "name")
    op.drop_column("users", "google_sub")
