"""Add store customers and link orders to customer records."""

import sqlalchemy as sa
from alembic import op

revision = "0028_customers"
down_revision = "0027_audit_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("store_id", "phone", name="uq_customers_store_phone"),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_customers_store_active", "customers", ["store_id", "is_active"])
    op.create_index("ix_customers_store_name", "customers", ["store_id", "last_name", "first_name"])
    op.create_index("ix_customers_store_email", "customers", ["store_id", "email"])

    op.add_column("orders", sa.Column("customer_id", sa.BigInteger(), nullable=True))
    op.create_index("ix_orders_store_customer", "orders", ["store_id", "customer_id"])
    op.create_foreign_key("fk_orders_customer_id", "orders", "customers", ["customer_id"], ["id"], ondelete="SET NULL")

    bind = op.get_bind()
    bind.execute(sa.text(
        "INSERT INTO customers (public_id, store_id, first_name, last_name, email, phone) "
        "SELECT SUBSTRING(MD5(CONCAT(store_id, ':', customer_phone)), 1, 32), store_id, "
        "MIN(customer_first_name), MIN(customer_last_name), MIN(customer_email), customer_phone "
        "FROM orders GROUP BY store_id, customer_phone"
    ))
    bind.execute(sa.text(
        "UPDATE orders o JOIN customers c ON c.store_id = o.store_id AND c.phone = o.customer_phone "
        "SET o.customer_id = c.id"
    ))


def downgrade() -> None:
    op.drop_constraint("fk_orders_customer_id", "orders", type_="foreignkey")
    op.drop_index("ix_orders_store_customer", table_name="orders")
    op.drop_column("orders", "customer_id")
    op.drop_index("ix_customers_store_email", table_name="customers")
    op.drop_index("ix_customers_store_name", table_name="customers")
    op.drop_index("ix_customers_store_active", table_name="customers")
    op.drop_table("customers")
