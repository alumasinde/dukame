"""Mark email column as case-insensitive.

Revision ID: 0004_email_collation
Revises: 0003_rbac_recovery
"""

from alembic import op

revision = "0004_email_collation"
down_revision = "0003_rbac_recovery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE users MODIFY COLUMN email VARCHAR(255) "
        "COLLATE utf8mb4_unicode_ci NOT NULL"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE users MODIFY COLUMN email VARCHAR(255) "
        "COLLATE utf8mb4_general_ci NOT NULL"
    )
