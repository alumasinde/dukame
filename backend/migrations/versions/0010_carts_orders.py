"""add carts and orders

Revision ID: 0010_carts_orders
Revises: 0009_business_types
"""
import uuid

import sqlalchemy as sa
from alembic import op

revision = "0010_carts_orders"
down_revision = "0009_business_types"
branch_labels = None
depends_on = None

ORDER_STATUSES = (
    ("pending", "Pending", "Order has been received and is awaiting processing.", 10, True, False),
    ("confirmed", "Confirmed", "Order has been accepted for fulfilment.", 20, False, False),
    ("processing", "Processing", "Order is being prepared.", 30, False, False),
    ("ready", "Ready", "Order is ready for collection or dispatch.", 40, False, False),
    ("completed", "Completed", "Order has been fulfilled.", 50, False, True),
    ("cancelled", "Cancelled", "Order has been cancelled.", 60, False, True),
)

PERMISSIONS = (
    ("orders.read", "View orders"),
    ("orders.manage", "Manage orders"),
)


def upgrade() -> None:
    op.create_table(
        "order_statuses",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_initial", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("is_terminal", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("code"),
        mysql_engine="InnoDB",
    )
    status_table = sa.table(
        "order_statuses",
        sa.column("public_id", sa.String),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.String),
        sa.column("sort_order", sa.Integer),
        sa.column("is_initial", sa.Boolean),
        sa.column("is_terminal", sa.Boolean),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        status_table,
        [
            {"public_id": uuid.uuid4().hex, "code": code, "name": name, "description": description, "sort_order": order, "is_initial": initial, "is_terminal": terminal, "is_active": True}
            for code, name, description, order, initial, terminal in ORDER_STATUSES
        ],
    )

    op.create_table(
        "carts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("session_token_hash", sa.String(length=64), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("checked_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("session_token_hash"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_carts_store_checked_out", "carts", ["store_id", "checked_out_at"])
    op.create_index("ix_carts_expires_at", "carts", ["expires_at"])

    op.create_table(
        "cart_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("cart_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("variant_id", sa.BigInteger(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_minor", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.ForeignKeyConstraint(["cart_id"], ["carts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"], ondelete="RESTRICT"),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_cart_items_cart", "cart_items", ["cart_id"])
    op.create_index("ix_cart_items_product_variant", "cart_items", ["product_id", "variant_id"])

    op.create_table(
        "orders",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("status_id", sa.BigInteger(), nullable=False),
        sa.Column("order_number", sa.String(length=32), nullable=False),
        sa.Column("customer_first_name", sa.String(length=100), nullable=False),
        sa.Column("customer_last_name", sa.String(length=100), nullable=False),
        sa.Column("customer_email", sa.String(length=320), nullable=True),
        sa.Column("customer_phone", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("subtotal_minor", sa.Integer(), nullable=False),
        sa.Column("total_minor", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("order_number"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["status_id"], ["order_statuses.id"], ondelete="RESTRICT"),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_orders_store_status_created", "orders", ["store_id", "status_id", "created_at"])
    op.create_index("ix_orders_store_customer_phone", "orders", ["store_id", "customer_phone"])

    op.create_table(
        "order_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("variant_id", sa.BigInteger(), nullable=True),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("variant_label", sa.String(length=500), nullable=True),
        sa.Column("sku", sa.String(length=100), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_minor", sa.Integer(), nullable=False),
        sa.Column("line_total_minor", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"], ondelete="RESTRICT"),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_order_items_order", "order_items", ["order_id"])

    permission_table = sa.table(
        "permissions",
        sa.column("public_id", sa.String),
        sa.column("key", sa.String),
        sa.column("name", sa.String),
    )
    op.bulk_insert(
        permission_table,
        [{"public_id": uuid.uuid4().hex, "key": key, "name": name} for key, name in PERMISSIONS],
    )
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "INSERT INTO tenant_role_permissions (role_id, permission_id) "
            "SELECT tr.id, p.id FROM tenant_roles tr CROSS JOIN permissions p "
            "WHERE tr.slug IN ('owner', 'admin') AND p.key IN ('orders.read', 'orders.manage')"
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM tenant_role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE key IN ('orders.read', 'orders.manage'))"))
    bind.execute(sa.text("DELETE FROM permissions WHERE key IN ('orders.read', 'orders.manage')"))
    op.drop_index("ix_order_items_order", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_orders_store_customer_phone", table_name="orders")
    op.drop_index("ix_orders_store_status_created", table_name="orders")
    op.drop_table("orders")
    op.drop_index("ix_cart_items_product_variant", table_name="cart_items")
    op.drop_index("ix_cart_items_cart", table_name="cart_items")
    op.drop_table("cart_items")
    op.drop_index("ix_carts_expires_at", table_name="carts")
    op.drop_index("ix_carts_store_checked_out", table_name="carts")
    op.drop_table("carts")
    op.drop_table("order_statuses")
