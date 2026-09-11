"""Synchronize commerce model changes with the database schema."""

import sqlalchemy as sa
from alembic import op

revision = "0012_sync_commerce_schema"
down_revision = "0011_harden_commerce_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("order_items", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.alter_column("order_statuses", "description", existing_type=sa.String(length=500), type_=sa.Text(), existing_nullable=True)


def downgrade() -> None:
    op.alter_column("order_statuses", "description", existing_type=sa.Text(), type_=sa.String(length=500), existing_nullable=True)
    op.drop_column("order_items", "created_at")
