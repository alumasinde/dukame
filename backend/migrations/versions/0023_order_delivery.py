"""Create order delivery workflow storage."""

import sqlalchemy as sa
from alembic import op

revision = "0023_order_delivery"
down_revision = "0022_inventory_movement_idemp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "order_deliveries",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("assigned_user_id", sa.BigInteger(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("delivery_note", sa.Text(), nullable=True),
        sa.Column("otp_hash", sa.String(length=64), nullable=True),
        sa.Column("otp_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("otp_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("otp_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["delivered_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id", name="uq_order_deliveries_public_id"),
        sa.UniqueConstraint("order_id", name="uq_order_deliveries_order"),
    )
    op.create_index("ix_order_deliveries_store_status", "order_deliveries", ["store_id", "status"])
    op.create_index("ix_order_deliveries_store_assigned", "order_deliveries", ["store_id", "assigned_user_id"])


def downgrade() -> None:
    op.drop_index("ix_order_deliveries_store_assigned", table_name="order_deliveries")
    op.drop_index("ix_order_deliveries_store_status", table_name="order_deliveries")
    op.drop_table("order_deliveries")
