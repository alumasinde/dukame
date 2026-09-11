"""add database-driven business types

Revision ID: 0009_business_types
Revises: 0008_product_media
"""
import uuid

import sqlalchemy as sa
from alembic import op

revision = "0009_business_types"
down_revision = "0008_product_media"
branch_labels = None
depends_on = None

BUSINESS_TYPES = (
    ("Fashion & Boutique", "fashion-boutique", "Clothing, footwear, bags and fashion accessories.", "fa-shirt", 10),
    ("Electronics", "electronics", "Phones, computers, appliances and electronic accessories.", "fa-mobile-screen-button", 20),
    ("Beauty & Cosmetics", "beauty-cosmetics", "Beauty products, cosmetics, skincare and personal care.", "fa-wand-magic-sparkles", 30),
    ("Food & Restaurant", "food-restaurant", "Restaurants, cafes, food vendors and catering businesses.", "fa-utensils", 40),
    ("Grocery & Supermarket", "grocery-supermarket", "Groceries, household essentials and everyday goods.", "fa-basket-shopping", 50),
    ("Hardware & Building", "hardware-building", "Hardware, tools, building materials and equipment.", "fa-screwdriver-wrench", 60),
    ("Health & Pharmacy", "health-pharmacy", "Pharmacies, wellness products and health-related retail.", "fa-heart-pulse", 70),
    ("Furniture & Home", "furniture-home", "Furniture, home goods, decor and household products.", "fa-couch", 80),
    ("Books & Stationery", "books-stationery", "Books, stationery, school and office supplies.", "fa-book", 90),
    ("Automotive", "automotive", "Vehicle parts, accessories, tools and automotive products.", "fa-car", 100),
    ("Agriculture", "agriculture", "Farm supplies, produce, livestock products and agricultural goods.", "fa-seedling", 110),
    ("Services", "services", "Businesses primarily selling services rather than physical products.", "fa-briefcase", 120),
    ("Other", "other", "Other businesses that do not fit the available categories.", "fa-store", 999),
)


def upgrade() -> None:
    op.create_table(
        "business_types",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(length=100), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("slug"),
        mysql_engine="InnoDB",
    )
    business_types = sa.table(
        "business_types",
        sa.column("public_id", sa.String),
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("description", sa.Text),
        sa.column("icon", sa.String),
        sa.column("sort_order", sa.Integer),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        business_types,
        [
            {"public_id": uuid.uuid4().hex, "name": name, "slug": slug, "description": description, "icon": icon, "sort_order": order, "is_active": True}
            for name, slug, description, icon, order in BUSINESS_TYPES
        ],
    )
    op.add_column("tenants", sa.Column("business_type_id", sa.BigInteger(), nullable=True))
    op.create_index("ix_tenants_business_type_id", "tenants", ["business_type_id"])
    op.create_foreign_key("fk_tenants_business_type_id", "tenants", "business_types", ["business_type_id"], ["id"], ondelete="RESTRICT")
    op.execute(
        sa.text(
            "UPDATE tenants SET business_type_id = (SELECT id FROM business_types WHERE slug = 'other') WHERE business_type_id IS NULL"
        )
    )
    op.alter_column("tenants", "business_type_id", existing_type=sa.BigInteger(), nullable=False)


def downgrade() -> None:
    op.drop_constraint("fk_tenants_business_type_id", "tenants", type_="foreignkey")
    op.drop_index("ix_tenants_business_type_id", table_name="tenants")
    op.drop_column("tenants", "business_type_id")
    op.drop_table("business_types")
