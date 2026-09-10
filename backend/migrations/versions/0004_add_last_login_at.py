"""add last login timestamp

Revision ID: 0004_last_login
Revises: 0003_rbac
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_last_login"
down_revision = "0003_rbac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "last_login_at")
