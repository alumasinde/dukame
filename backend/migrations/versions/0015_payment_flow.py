"""Add store payment methods, payment state, attempts, and callback events."""

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0015_payment_flow"
down_revision = "0014_tracking_hash_compat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("payment_methods", sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False), sa.Column("public_id", sa.String(length=32), nullable=False), sa.Column("store_id", sa.BigInteger(), nullable=False), sa.Column("code", sa.String(length=32), nullable=False), sa.Column("name", sa.String(length=100), nullable=False), sa.Column("is_enabled", sa.Boolean(), server_default=sa.true(), nullable=False), sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False), sa.Column("instructions", sa.Text(), nullable=True), sa.Column("config_encrypted", sa.Text(), nullable=True), sa.Column("callback_token_hash", sa.String(length=64), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("public_id"), sa.UniqueConstraint("callback_token_hash"), sa.UniqueConstraint("store_id", "code", name="uq_payment_methods_store_code"), mysql_engine="InnoDB")
    op.create_index("ix_payment_methods_store_enabled", "payment_methods", ["store_id", "is_enabled", "sort_order"])
    op.create_table("payments", sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False), sa.Column("public_id", sa.String(length=32), nullable=False), sa.Column("store_id", sa.BigInteger(), nullable=False), sa.Column("order_id", sa.BigInteger(), nullable=False), sa.Column("payment_method_id", sa.BigInteger(), nullable=False), sa.Column("status", sa.String(length=32), server_default="pending", nullable=False), sa.Column("amount_minor", sa.Integer(), nullable=False), sa.Column("currency", sa.String(length=3), nullable=False), sa.Column("customer_phone", sa.String(length=32), nullable=False), sa.Column("provider_reference", sa.String(length=128), nullable=True), sa.Column("provider_status_code", sa.String(length=64), nullable=True), sa.Column("failure_reason", sa.String(length=1000), nullable=True), sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["payment_method_id"], ["payment_methods.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("public_id"), sa.UniqueConstraint("order_id"), mysql_engine="InnoDB")
    op.create_index("ix_payments_store_status_created", "payments", ["store_id", "status", "created_at"])
    op.create_index("ix_payments_provider_reference", "payments", ["provider_reference"])
    op.create_table("payment_attempts", sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False), sa.Column("public_id", sa.String(length=32), nullable=False), sa.Column("payment_id", sa.BigInteger(), nullable=False), sa.Column("attempt_number", sa.Integer(), nullable=False), sa.Column("status", sa.String(length=32), server_default="created", nullable=False), sa.Column("provider_request_id", sa.String(length=128), nullable=True), sa.Column("provider_checkout_request_id", sa.String(length=128), nullable=True), sa.Column("phone", sa.String(length=32), nullable=False), sa.Column("amount_minor", sa.Integer(), nullable=False), sa.Column("provider_response_code", sa.String(length=64), nullable=True), sa.Column("provider_response_message", sa.String(length=1000), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("public_id"), sa.UniqueConstraint("provider_checkout_request_id"), mysql_engine="InnoDB")
    op.create_table("payment_events", sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False), sa.Column("public_id", sa.String(length=32), nullable=False), sa.Column("payment_id", sa.BigInteger(), nullable=False), sa.Column("event_key", sa.String(length=128), nullable=False), sa.Column("event_type", sa.String(length=64), nullable=False), sa.Column("payload_hash", sa.String(length=64), nullable=False), sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("public_id"), sa.UniqueConstraint("event_key"), mysql_engine="InnoDB")
    op.create_index("ix_payment_events_payment_created", "payment_events", ["payment_id", "created_at"])
    bind = op.get_bind()
    stores = bind.execute(sa.text("SELECT id FROM stores")).fetchall()
    payment_methods = sa.table("payment_methods", sa.column("public_id", sa.String), sa.column("store_id", sa.BigInteger), sa.column("code", sa.String), sa.column("name", sa.String), sa.column("is_enabled", sa.Boolean), sa.column("sort_order", sa.Integer), sa.column("instructions", sa.Text))
    for store in stores:
        bind.execute(sa.insert(payment_methods).values(public_id=uuid.uuid4().hex, store_id=store[0], code="cash", name="Cash", is_enabled=True, sort_order=10, instructions="Pay the store in cash when your order is delivered or collected."))
    permission_table = sa.table("permissions", sa.column("id", sa.BigInteger), sa.column("public_id", sa.String(32)), sa.column("key", sa.String(150)), sa.column("name", sa.String(150)))
    for key, name in (("payments.read", "View payments"), ("payments.manage", "Manage payments")):
        if bind.execute(sa.select(permission_table.c.id).where(permission_table.c.key == key)).scalar() is None:
            bind.execute(sa.insert(permission_table).values(public_id=uuid.uuid4().hex, key=key, name=name))
    permission_ids = {key: bind.execute(sa.select(permission_table.c.id).where(permission_table.c.key == key)).scalar_one() for key in ("payments.read", "payments.manage")}
    bind.execute(sa.text("INSERT INTO tenant_role_permissions (role_id, permission_id) SELECT tr.id, :permission_id FROM tenant_roles tr WHERE tr.slug IN ('owner','admin','manager') AND NOT EXISTS (SELECT 1 FROM tenant_role_permissions x WHERE x.role_id = tr.id AND x.permission_id = :permission_id)"), {"permission_id": permission_ids["payments.manage"]})
    bind.execute(sa.text("INSERT INTO tenant_role_permissions (role_id, permission_id) SELECT tr.id, :permission_id FROM tenant_roles tr WHERE tr.slug IN ('owner','admin','manager','staff') AND NOT EXISTS (SELECT 1 FROM tenant_role_permissions x WHERE x.role_id = tr.id AND x.permission_id = :permission_id)"), {"permission_id": permission_ids["payments.read"]})


def downgrade() -> None:
    bind = op.get_bind()
    permission_table = sa.table("permissions", sa.column("id", sa.BigInteger), sa.column("key", sa.String(150)))
    for key in ("payments.manage", "payments.read"):
        permission_id = bind.execute(sa.select(permission_table.c.id).where(permission_table.c.key == key)).scalar()
        if permission_id is not None:
            bind.execute(sa.text("DELETE FROM tenant_role_permissions WHERE permission_id = :permission_id"), {"permission_id": permission_id})
            bind.execute(sa.text("DELETE FROM permissions WHERE id = :permission_id"), {"permission_id": permission_id})
    op.drop_index("ix_payment_events_payment_created", table_name="payment_events")
    op.drop_table("payment_events")
    op.drop_table("payment_attempts")
    op.drop_index("ix_payments_provider_reference", table_name="payments")
    op.drop_index("ix_payments_store_status_created", table_name="payments")
    op.drop_table("payments")
    op.drop_index("ix_payment_methods_store_enabled", table_name="payment_methods")
    op.drop_table("payment_methods")
