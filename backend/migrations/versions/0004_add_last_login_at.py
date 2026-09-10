"""Mark email column as case-insensitive.

Revision ID: 0004_email_collation
Revises: 0003_rbac_recovery
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_email_collation"
down_revision = "0003_rbac_recovery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Note: last_login_at was already added in migration 0002
    # This migration ensures email column has case-insensitive collation for MySQL
    op.execute("ALTER TABLE users MODIFY COLUMN email VARCHAR(255) COLLATE utf8mb4_unicode_ci")


def downgrade() -> None:
    # Revert to default collation (not strictly necessary, but included for completeness)
    op.execute("ALTER TABLE users MODIFY COLUMN email VARCHAR(255) COLLATE utf8mb4_general_ci")
