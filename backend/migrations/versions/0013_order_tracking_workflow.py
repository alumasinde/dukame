"""Add secure order tracking, status history, transitions, and notifications."""

import hashlib
import secrets

import sqlalchemy as sa
from alembic import op

revision = "0013_order_tracking_workflow"
down_revision = "0012_sync_commerce_schema"
branch_labels = None
depends_on = None


TRANSITIONS = (
    ("pending", "confirmed"),
    ("pending", "cancelled"),
    ("confirmed", "processing"),
    ("confirmed", "cancelled"),
    ("processing", "ready"),
    ("processing", "cancelled"),
    ("ready", "completed"),
)


def upgrade() -> None:
    op.add_column("orders", sa.Column("tracking_token_hash", sa.String(length=64), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id FROM orders WHERE tracking_token_hash IS NULL")).fetchall()
    for row in rows:
        token = secrets.token_urlsafe(32)
        bind.execute(
            sa.text("UPDATE orders SET tracking_token_hash = :token_hash WHERE id = :id"),
            {"token_hash": hashlib.sha256(token.encode("utf-8")).hexdigest(), "id": row[0]},
        )
    op.alter_column("orders", "tracking_token_hash", existing_type=sa.String(length=64), nullable=False)
    op.create_unique_constraint("uq_orders_tracking_token_hash", "orders", ["tracking_token_hash"])

    op.create_table(
        "order_status_transitions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("from_status_id", sa.BigInteger(), nullable=False),
        sa.Column("to_status_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["from_status_id"], ["order_statuses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_status_id"], ["order_statuses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("from_status_id", "to_status_id", name="uq_order_status_transition"),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_order_status_transitions_from", "order_status_transitions", ["from_status_id"])

    status_table = sa.table("order_statuses", sa.column("id", sa.BigInteger), sa.column("code", sa.String))
    transition_table = sa.table(
        "order_status_transitions",
        sa.column("from_status_id", sa.BigInteger),
        sa.column("to_status_id", sa.BigInteger),
    )
    status_ids = {
        row.code: row.id
        for row in bind.execute(sa.select(status_table.c.id, status_table.c.code)).fetchall()
    }
    op.bulk_insert(
        transition_table,
        [
            {"from_status_id": status_ids[from_code], "to_status_id": status_ids[to_code]}
            for from_code, to_code in TRANSITIONS
            if from_code in status_ids and to_code in status_ids
        ],
    )

    op.create_table(
        "order_status_history",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("status_id", sa.BigInteger(), nullable=False),
        sa.Column("actor_user_id", sa.BigInteger(), nullable=True),
        sa.Column("source", sa.String(length=32), server_default="merchant", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["status_id"], ["order_statuses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_order_status_history_order_created", "order_status_history", ["order_id", "created_at"])

    pending_status_id = status_ids.get("pending")
    if pending_status_id is not None:
        op.execute(
            sa.text(
                "INSERT INTO order_status_history (order_id, status_id, source) "
                "SELECT id, status_id, 'migration' FROM orders "
                "WHERE status_id = :status_id AND NOT EXISTS ("
                "SELECT 1 FROM order_status_history h WHERE h.order_id = orders.id"
                ")"
            ).bindparams(status_id=pending_status_id)
        )
    op.execute(
        sa.text(
            "INSERT INTO order_status_history (order_id, status_id, source) "
            "SELECT o.id, o.status_id, 'migration' FROM orders o "
            "WHERE NOT EXISTS (SELECT 1 FROM order_status_history h WHERE h.order_id = o.id)"
        )
    )

    op.create_table(
        "order_notifications",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("status_id", sa.BigInteger(), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("recipient", sa.String(length=320), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("tracking_url", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["status_id"], ["order_statuses.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", "status_id", "channel", name="uq_order_notification_status_channel"),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_order_notifications_queue", "order_notifications", ["status", "available_at"])


def downgrade() -> None:
    op.drop_index("ix_order_notifications_queue", table_name="order_notifications")
    op.drop_table("order_notifications")
    op.drop_index("ix_order_status_history_order_created", table_name="order_status_history")
    op.drop_table("order_status_history")
    op.drop_index("ix_order_status_transitions_from", table_name="order_status_transitions")
    op.drop_table("order_status_transitions")
    op.drop_constraint("uq_orders_tracking_token_hash", "orders", type_="unique")
    op.drop_column("orders", "tracking_token_hash")
