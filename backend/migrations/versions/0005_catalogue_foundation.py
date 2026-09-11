"""Add store, category and product catalogue foundation."""
import uuid

import sqlalchemy as sa
from alembic import op

revision = "0005_catalogue_foundation"
down_revision = "0004_email_collation"
branch_labels = None
depends_on = None

PERMISSIONS = (
    ("catalogue.read", "View store catalogue"),
    ("catalogue.manage", "Manage store catalogue"),
)



def upgrade() -> None:
    op.create_table(
        "stores",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("tenant_id", name="uq_stores_tenant"),
        sa.UniqueConstraint("slug"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_stores_status", "stores", ["status"])

    op.create_table(
        "categories",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("parent_id", sa.BigInteger(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("store_id", "slug", name="uq_categories_store_slug"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["categories.id"], ondelete="SET NULL"),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_categories_store_status", "categories", ["store_id", "status"])
    op.create_index("ix_categories_store_parent", "categories", ["store_id", "parent_id"])

    op.create_table(
        "products",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("category_id", sa.BigInteger(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("sku", sa.String(length=100), nullable=True),
        sa.Column("price_minor", sa.Integer(), nullable=False),
        sa.Column("compare_at_price_minor", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("inventory_tracking", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("inventory_quantity", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("store_id", "slug", name="uq_products_store_slug"),
        sa.UniqueConstraint("store_id", "sku", name="uq_products_store_sku"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_products_store_status", "products", ["store_id", "status"])
    op.create_index("ix_products_store_category", "products", ["store_id", "category_id"])

    permission_table = sa.table(
        "permissions",
        sa.column("public_id", sa.String()),
        sa.column("key", sa.String()),
        sa.column("name", sa.String()),
    )
    op.bulk_insert(permission_table, [{"public_id": uuid.uuid4().hex, "key": key, "name": name} for key, name in PERMISSIONS])

    bind = op.get_bind()
    bind.execute(sa.text(
        "INSERT INTO tenant_role_permissions (role_id, permission_id) "
        "SELECT tr.id, p.id FROM tenant_roles tr CROSS JOIN permissions p "
        "WHERE tr.slug IN ('owner', 'admin', 'manager') AND p.key IN ('catalogue.read', 'catalogue.manage')"
    ))
    bind.execute(sa.text(
        "INSERT INTO tenant_role_permissions (role_id, permission_id) "
        "SELECT tr.id, p.id FROM tenant_roles tr CROSS JOIN permissions p "
        "WHERE tr.slug = 'staff' AND p.key = 'catalogue.read'"
    ))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text(
        "DELETE trp FROM tenant_role_permissions trp "
        "JOIN permissions p ON p.id = trp.permission_id "
        "WHERE p.key IN ('catalogue.read', 'catalogue.manage')"
    ))
    bind.execute(sa.text("DELETE FROM permissions WHERE key IN ('catalogue.read', 'catalogue.manage')"))
    op.drop_index("ix_products_store_category", table_name="products")
    op.drop_index("ix_products_store_status", table_name="products")
    op.drop_table("products")
    op.drop_index("ix_categories_store_parent", table_name="categories")
    op.drop_index("ix_categories_store_status", table_name="categories")
    op.drop_table("categories")
    op.drop_index("ix_stores_status", table_name="stores")
    op.drop_table("stores")
