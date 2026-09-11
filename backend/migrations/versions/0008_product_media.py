"""Add product media."""

import sqlalchemy as sa
from alembic import op

revision = "0008_product_media"
down_revision = "0007_variant_store_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_media",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("alt_text", sa.String(length=255), nullable=True),
        sa.Column("media_type", sa.String(length=32), nullable=False, server_default="image"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_product_media_store_product", "product_media", ["store_id", "product_id"])
    op.create_index("ix_product_media_product_sort", "product_media", ["product_id", "sort_order"])
    op.create_index("ix_product_media_product_status", "product_media", ["product_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_product_media_product_status", table_name="product_media")
    op.drop_index("ix_product_media_product_sort", table_name="product_media")
    op.drop_index("ix_product_media_store_product", table_name="product_media")
    op.drop_table("product_media")
