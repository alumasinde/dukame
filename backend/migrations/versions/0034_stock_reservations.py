"""
Database migration to add stock reservation table.
Creates the structure for holding inventory during pending payment.
"""

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        "stock_reservations",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("public_id", sa.String(32), nullable=False, unique=True),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("order_id", sa.BigInteger(), nullable=True),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("variant_id", sa.BigInteger(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("reserved_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("release_reason", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKey("stores.id", name="fk_stock_reservations_store_id", ondelete="CASCADE"),
        sa.ForeignKey("orders.id", name="fk_stock_reservations_order_id", ondelete="CASCADE"),
        sa.ForeignKey("products.id", name="fk_stock_reservations_product_id", ondelete="CASCADE"),
        sa.ForeignKey("product_variants.id", name="fk_stock_reservations_variant_id", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    
    op.create_index(
        "ix_stock_reservations_store_status",
        "stock_reservations",
        ["store_id", "status"],
    )
    op.create_index(
        "ix_stock_reservations_order",
        "stock_reservations",
        ["order_id"],
    )
    op.create_index(
        "ix_stock_reservations_product_variant",
        "stock_reservations",
        ["product_id", "variant_id"],
    )
    op.create_index(
        "ix_stock_reservations_expires",
        "stock_reservations",
        ["expires_at"],
    )


def downgrade():
    op.drop_index("ix_stock_reservations_expires", "stock_reservations")
    op.drop_index("ix_stock_reservations_product_variant", "stock_reservations")
    op.drop_index("ix_stock_reservations_order", "stock_reservations")
    op.drop_index("ix_stock_reservations_store_status", "stock_reservations")
    op.drop_table("stock_reservations")
