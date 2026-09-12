"""complete subscription module: plan metadata, public catalog, feature seeds

Revision ID: 0031_subscription_module
Revises: 0030_store_notification_channels
"""

from __future__ import annotations

import json
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0031_subscription_module"
down_revision = "0030_store_notification_channels"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    return column in {c["name"] for c in inspect(bind).get_columns(table)}


def _has_index(table: str, name: str) -> bool:
    bind = op.get_bind()
    return any(idx["name"] == name for idx in inspect(bind).get_indexes(table))


def upgrade() -> None:
    if not _has_column("plans", "trial_days"):
        op.add_column(
            "plans",
            sa.Column("trial_days", sa.Integer(), server_default="0", nullable=False),
        )
    if not _has_column("plans", "sort_order"):
        op.add_column(
            "plans",
            sa.Column("sort_order", sa.Integer(), server_default="100", nullable=False),
        )
    if not _has_column("plans", "is_public"):
        op.add_column(
            "plans",
            sa.Column("is_public", sa.Boolean(), server_default="1", nullable=False),
        )
    if not _has_column("plans", "badge"):
        op.add_column(
            "plans",
            sa.Column("badge", sa.String(length=64), nullable=True),
        )
    if not _has_column("plans", "highlight"):
        op.add_column(
            "plans",
            sa.Column("highlight", sa.Boolean(), server_default="0", nullable=False),
        )

    if not _has_index("plans", "ix_plans_public_sort"):
        op.create_index(
            "ix_plans_public_sort",
            "plans",
            ["is_public", "is_active", "sort_order"],
            unique=False,
        )

    plans = sa.table(
        "plans",
        sa.column("id", sa.BigInteger),
        sa.column("public_id", sa.String),
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("monthly_price_minor", sa.Integer),
        sa.column("quarterly_price_minor", sa.Integer),
        sa.column("yearly_price_minor", sa.Integer),
        sa.column("currency", sa.String),
        sa.column("trial_days", sa.Integer),
        sa.column("is_active", sa.Boolean),
        sa.column("is_public", sa.Boolean),
        sa.column("sort_order", sa.Integer),
        sa.column("badge", sa.String),
        sa.column("highlight", sa.Boolean),
    )
    features = sa.table(
        "plan_features",
        sa.column("id", sa.BigInteger),
        sa.column("plan_id", sa.BigInteger),
        sa.column("feature_key", sa.String),
        sa.column("value", sa.JSON),
    )

    bind = op.get_bind()
    existing = {
        row[0]: row[1]
        for row in bind.execute(sa.text("SELECT slug, id FROM plans")).fetchall()
    }

    catalog = [
        {
            "slug": "free",
            "name": "Free",
            "description": "Get started with a simple online shop. Ideal for testing and very small catalogues.",
            "monthly_price_minor": 0,
            "quarterly_price_minor": 0,
            "yearly_price_minor": 0,
            "currency": "KES",
            "trial_days": 0,
            "sort_order": 10,
            "badge": None,
            "highlight": False,
            "features": {
                "stores": 1,
                "products": 25,
                "staff_seats": 1,
                "orders_per_month": 50,
                "custom_domain": False,
                "whatsapp_notifications": False,
                "priority_support": False,
            },
        },
        {
            "slug": "starter",
            "name": "Starter",
            "description": "For growing dukas that need more products, staff and order volume.",
            "monthly_price_minor": 99900,
            "quarterly_price_minor": 269700,
            "yearly_price_minor": 959000,
            "currency": "KES",
            "trial_days": 14,
            "sort_order": 20,
            "badge": "Most popular",
            "highlight": True,
            "features": {
                "stores": 1,
                "products": 200,
                "staff_seats": 3,
                "orders_per_month": 500,
                "custom_domain": True,
                "whatsapp_notifications": True,
                "priority_support": False,
            },
        },
        {
            "slug": "growth",
            "name": "Growth",
            "description": "Multi-store ready merchants with higher limits and priority support.",
            "monthly_price_minor": 249900,
            "quarterly_price_minor": 674700,
            "yearly_price_minor": 2399000,
            "currency": "KES",
            "trial_days": 14,
            "sort_order": 30,
            "badge": None,
            "highlight": False,
            "features": {
                "stores": 3,
                "products": 2000,
                "staff_seats": 10,
                "orders_per_month": 5000,
                "custom_domain": True,
                "whatsapp_notifications": True,
                "priority_support": True,
            },
        },
        {
            "slug": "business",
            "name": "Business",
            "description": "High-volume operations with expanded limits for established brands.",
            "monthly_price_minor": 499900,
            "quarterly_price_minor": 1349700,
            "yearly_price_minor": 4799000,
            "currency": "KES",
            "trial_days": 14,
            "sort_order": 40,
            "badge": None,
            "highlight": False,
            "features": {
                "stores": 10,
                "products": 10000,
                "staff_seats": 25,
                "orders_per_month": 25000,
                "custom_domain": True,
                "whatsapp_notifications": True,
                "priority_support": True,
            },
        },
    ]

    for item in catalog:
        slug = item["slug"]
        feature_map = item["features"]
        payload = {k: v for k, v in item.items() if k not in {"slug", "features"}}

        if slug in existing:
            plan_id = existing[slug]
            bind.execute(
                sa.text(
                    """
                    UPDATE plans SET
                        name = :name,
                        description = :description,
                        monthly_price_minor = :monthly_price_minor,
                        quarterly_price_minor = :quarterly_price_minor,
                        yearly_price_minor = :yearly_price_minor,
                        currency = :currency,
                        trial_days = :trial_days,
                        is_active = 1,
                        is_public = 1,
                        sort_order = :sort_order,
                        badge = :badge,
                        highlight = :highlight
                    WHERE id = :id
                    """
                ),
                {"id": plan_id, **payload},
            )
        else:
            result = bind.execute(
                plans.insert().values(
                    public_id=uuid.uuid4().hex,
                    slug=slug,
                    is_active=True,
                    is_public=True,
                    **payload,
                )
            )
            plan_id = result.lastrowid
            if not plan_id:
                plan_id = bind.execute(
                    sa.text("SELECT id FROM plans WHERE slug = :slug"), {"slug": slug}
                ).scalar()

        for key, value in feature_map.items():
            existing_feature_id = bind.execute(
                sa.text(
                    "SELECT id FROM plan_features WHERE plan_id = :plan_id AND feature_key = :key"
                ),
                {"plan_id": plan_id, "key": key},
            ).scalar()
            encoded = json.dumps(value)
            if existing_feature_id:
                bind.execute(
                    sa.text("UPDATE plan_features SET value = CAST(:value AS JSON) WHERE id = :id"),
                    {"id": existing_feature_id, "value": encoded},
                )
            else:
                bind.execute(
                    features.insert().values(
                        plan_id=plan_id, feature_key=key, value=value
                    )
                )


def downgrade() -> None:
    if _has_index("plans", "ix_plans_public_sort"):
        op.drop_index("ix_plans_public_sort", table_name="plans")
    for col in ("highlight", "badge", "is_public", "sort_order"):
        if _has_column("plans", col):
            op.drop_column("plans", col)
