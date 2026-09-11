"""Scope variants to stores for SKU integrity."""

import sqlalchemy as sa
from alembic import op

revision = "0007_variant_store_scope"
down_revision = "0006_product_options_variants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("product_variants", sa.Column("store_id", sa.BigInteger(), nullable=True))
    op.execute("UPDATE product_variants pv JOIN products p ON p.id = pv.product_id SET pv.store_id = p.store_id")
    op.alter_column("product_variants", "store_id", nullable=False)
    op.create_foreign_key("fk_product_variants_store_id", "product_variants", "stores", ["store_id"], ["id"], ondelete="CASCADE")
    op.drop_constraint("uq_product_variants_product_sku", "product_variants", type_="unique")
    op.create_unique_constraint("uq_product_variants_store_sku", "product_variants", ["store_id", "sku"])
    op.create_index("ix_product_variants_store", "product_variants", ["store_id"])


def downgrade() -> None:
    op.drop_index("ix_product_variants_store", table_name="product_variants")
    op.drop_constraint("uq_product_variants_store_sku", "product_variants", type_="unique")
    op.create_unique_constraint("uq_product_variants_product_sku", "product_variants", ["product_id", "sku"])
    op.drop_constraint("fk_product_variants_store_id", "product_variants", type_="foreignkey")
    op.drop_column("product_variants", "store_id")
