"""Scope variants to stores for SKU integrity."""

import sqlalchemy as sa
from alembic import op

revision = "0007_variant_store_scope"
down_revision = "0006_product_options_variants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {column["name"] for column in inspector.get_columns("product_variants")}
    if "store_id" not in columns:
        op.add_column("product_variants", sa.Column("store_id", sa.BigInteger(), nullable=True))
        op.execute("UPDATE product_variants pv JOIN products p ON p.id = pv.product_id SET pv.store_id = p.store_id")

    op.alter_column(
        "product_variants",
        "store_id",
        existing_type=sa.BigInteger(),
        nullable=False,
    )

    foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys("product_variants")}
    if "fk_product_variants_store_id" not in foreign_keys:
        op.create_foreign_key(
            "fk_product_variants_store_id",
            "product_variants",
            "stores",
            ["store_id"],
            ["id"],
            ondelete="CASCADE",
        )

    unique_constraints = {constraint["name"] for constraint in inspector.get_unique_constraints("product_variants")}
    if "uq_product_variants_product_sku" in unique_constraints:
        op.drop_constraint("uq_product_variants_product_sku", "product_variants", type_="unique")

    if "uq_product_variants_store_sku" not in unique_constraints:
        op.create_unique_constraint(
            "uq_product_variants_store_sku",
            "product_variants",
            ["store_id", "sku"],
        )

    indexes = {index["name"] for index in inspector.get_indexes("product_variants")}
    if "ix_product_variants_store" not in indexes:
        op.create_index("ix_product_variants_store", "product_variants", ["store_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    indexes = {index["name"] for index in inspector.get_indexes("product_variants")}
    if "ix_product_variants_store" in indexes:
        op.drop_index("ix_product_variants_store", table_name="product_variants")

    unique_constraints = {constraint["name"] for constraint in inspector.get_unique_constraints("product_variants")}
    if "uq_product_variants_store_sku" in unique_constraints:
        op.drop_constraint("uq_product_variants_store_sku", "product_variants", type_="unique")
    if "uq_product_variants_product_sku" not in unique_constraints:
        op.create_unique_constraint("uq_product_variants_product_sku", "product_variants", ["product_id", "sku"])

    foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys("product_variants")}
    if "fk_product_variants_store_id" in foreign_keys:
        op.drop_constraint("fk_product_variants_store_id", "product_variants", type_="foreignkey")

    columns = {column["name"] for column in inspector.get_columns("product_variants")}
    if "store_id" in columns:
        op.drop_column("product_variants", "store_id")
