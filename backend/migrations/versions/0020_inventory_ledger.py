"""Add inventory movement ledger and non-negative stock constraints."""

import sqlalchemy as sa
from alembic import op

revision = "0020_inventory_ledger"
down_revision = "0019_commerce_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("variant_id", sa.BigInteger(), nullable=True),
        sa.Column("movement_type", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("quantity_before", sa.Integer(), nullable=False),
        sa.Column("quantity_after", sa.Integer(), nullable=False),
        sa.Column("reference_type", sa.String(length=32), nullable=True),
        sa.Column("reference_id", sa.String(length=64), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("actor_user_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id", name="uq_inventory_movements_public_id"),
        sa.CheckConstraint("quantity > 0", name="ck_inventory_movements_quantity_positive"),
        sa.CheckConstraint("quantity_before >= 0", name="ck_inventory_movements_quantity_before_nonnegative"),
        sa.CheckConstraint("quantity_after >= 0", name="ck_inventory_movements_quantity_after_nonnegative"),
        sa.CheckConstraint("movement_type in ('sale','return','restock','adjustment','damage','loss')", name="ck_inventory_movements_type"),
    )
    op.create_index("ix_inventory_movements_store_created", "inventory_movements", ["store_id", "created_at", "id"])
    op.create_index("ix_inventory_movements_product_created", "inventory_movements", ["product_id", "created_at", "id"])
    op.create_index("ix_inventory_movements_reference", "inventory_movements", ["reference_type", "reference_id"])

    op.create_check_constraint("ck_products_inventory_quantity_nonnegative", "products", "inventory_quantity >= 0")
    op.create_check_constraint("ck_product_variants_inventory_quantity_nonnegative", "product_variants", "inventory_quantity >= 0")


def downgrade() -> None:
    op.drop_constraint("ck_product_variants_inventory_quantity_nonnegative", "product_variants", type_="check")
    op.drop_constraint("ck_products_inventory_quantity_nonnegative", "products", type_="check")
    op.drop_index("ix_inventory_movements_reference", table_name="inventory_movements")
    op.drop_index("ix_inventory_movements_product_created", table_name="inventory_movements")
    op.drop_index("ix_inventory_movements_store_created", table_name="inventory_movements")
    op.drop_table("inventory_movements")
