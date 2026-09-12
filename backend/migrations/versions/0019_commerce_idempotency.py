"""Add durable idempotency keys for commerce write operations."""

import sqlalchemy as sa
from alembic import op

revision = "0019_commerce_idempotency"
down_revision = "0018_order_transition_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("scope_key", sa.String(length=64), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("resource_public_id", sa.String(length=32), nullable=False),
        sa.Column("response_status_code", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], name="fk_idempotency_keys_store", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id", "operation", "scope_key", "key", name="uq_idempotency_store_operation_scope_key"),
    )
    op.create_index("ix_idempotency_keys_store_created", "idempotency_keys", ["store_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_idempotency_keys_store_created", table_name="idempotency_keys")
    op.drop_table("idempotency_keys")
