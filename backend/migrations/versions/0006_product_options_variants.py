"""Add product options and variants."""

import sqlalchemy as sa
from alembic import op

revision = "0006_product_options_variants"
down_revision = "0005_catalogue_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_options",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("store_id", "slug", name="uq_product_options_store_slug"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_product_options_store_status", "product_options", ["store_id", "status"])

    op.create_table(
        "product_option_values",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("option_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("option_id", "slug", name="uq_product_option_values_option_slug"),
        sa.ForeignKeyConstraint(["option_id"], ["product_options.id"], ondelete="CASCADE"),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_product_option_values_option_status", "product_option_values", ["option_id", "status"])

    op.create_table(
        "product_variants",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("sku", sa.String(length=100), nullable=True),
        sa.Column("price_minor", sa.Integer(), nullable=True),
        sa.Column("compare_at_price_minor", sa.Integer(), nullable=True),
        sa.Column("inventory_tracking", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("inventory_quantity", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("product_id", "sku", name="uq_product_variants_product_sku"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_product_variants_product_status", "product_variants", ["product_id", "status"])

    op.create_table(
        "product_variant_option_values",
        sa.Column("variant_id", sa.BigInteger(), nullable=False),
        sa.Column("option_value_id", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("variant_id", "option_value_id"),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["option_value_id"], ["product_option_values.id"], ondelete="CASCADE"),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_variant_option_values_option_value", "product_variant_option_values", ["option_value_id"])


def downgrade() -> None:
    op.drop_index("ix_variant_option_values_option_value", table_name="product_variant_option_values")
    op.drop_table("product_variant_option_values")
    op.drop_index("ix_product_variants_product_status", table_name="product_variants")
    op.drop_table("product_variants")
    op.drop_index("ix_product_option_values_option_status", table_name="product_option_values")
    op.drop_table("product_option_values")
    op.drop_index("ix_product_options_store_status", table_name="product_options")
    op.drop_table("product_options")
