"""Add per-store notification toggles, WhatsApp fields, and customer opt-in."""

import sqlalchemy as sa
from alembic import op

revision = "0030_store_notification_channels"
down_revision = "0029_customer_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "stores",
        sa.Column("sms_notifications_enabled", sa.Boolean(), server_default="0", nullable=False),
    )
    op.add_column(
        "stores",
        sa.Column("whatsapp_notifications_enabled", sa.Boolean(), server_default="0", nullable=False),
    )
    op.add_column(
        "customers",
        sa.Column("whatsapp_opt_in_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "order_notifications",
        sa.Column("template_name", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "order_notifications",
        sa.Column("template_params", sa.JSON(), nullable=True),
    )
    op.add_column(
        "order_notifications",
        sa.Column("store_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_order_notifications_store_id",
        "order_notifications",
        "stores",
        ["store_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_order_notifications_store_channel", "order_notifications", ["store_id", "channel"])


def downgrade() -> None:
    op.drop_index("ix_order_notifications_store_channel", table_name="order_notifications")
    op.drop_constraint("fk_order_notifications_store_id", "order_notifications", type_="foreignkey")
    op.drop_column("order_notifications", "store_id")
    op.drop_column("order_notifications", "template_params")
    op.drop_column("order_notifications", "template_name")
    op.drop_column("customers", "whatsapp_opt_in_at")
    op.drop_column("stores", "whatsapp_notifications_enabled")
    op.drop_column("stores", "sms_notifications_enabled")
