"""Add notification worker leases for crash recovery."""

import sqlalchemy as sa
from alembic import op

revision = "0026_notification_leases"
down_revision = "0025_inventory_order_ref"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("order_notifications", sa.Column("worker_id", sa.String(64), nullable=True))
    op.add_column("order_notifications", sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "ix_order_notifications_processing_lease",
        "order_notifications",
        ["status", "lease_expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_order_notifications_processing_lease", table_name="order_notifications")
    op.drop_column("order_notifications", "lease_expires_at")
    op.drop_column("order_notifications", "worker_id")
