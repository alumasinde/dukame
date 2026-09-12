"""subscription invoices, payments, and usage meters

Revision ID: 0032_subscription_billing
Revises: 0031_subscription_module
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0032_subscription_billing"
down_revision = "0031_subscription_module"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscription_invoices",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("subscription_id", sa.BigInteger(), nullable=False),
        sa.Column("plan_id", sa.BigInteger(), nullable=False),
        sa.Column("billing_interval", sa.String(length=16), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="open", nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("idempotency_key"),
        mysql_engine="InnoDB",
    )
    op.create_index(
        "ix_subscription_invoices_tenant_status",
        "subscription_invoices",
        ["tenant_id", "status", "created_at"],
    )
    op.create_index(
        "ix_subscription_invoices_subscription_status",
        "subscription_invoices",
        ["subscription_id", "status"],
    )

    op.create_table(
        "subscription_payments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("invoice_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("provider", sa.String(length=32), server_default="mpesa", nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("provider_checkout_request_id", sa.String(length=128), nullable=True),
        sa.Column("provider_merchant_request_id", sa.String(length=128), nullable=True),
        sa.Column("provider_reference", sa.String(length=128), nullable=True),
        sa.Column("provider_status_code", sa.String(length=64), nullable=True),
        sa.Column("failure_reason", sa.String(length=1000), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["subscription_invoices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("provider_checkout_request_id"),
        mysql_engine="InnoDB",
    )
    op.create_index(
        "ix_subscription_payments_invoice_status",
        "subscription_payments",
        ["invoice_id", "status"],
    )

    op.create_table(
        "usage_meters",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("feature_key", sa.String(length=100), nullable=False),
        sa.Column("period_key", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "feature_key", "period_key", name="uq_usage_meters_tenant_feature_period"
        ),
        mysql_engine="InnoDB",
    )
    op.create_index(
        "ix_usage_meters_tenant_feature",
        "usage_meters",
        ["tenant_id", "feature_key"],
    )


def downgrade() -> None:
    op.drop_index("ix_usage_meters_tenant_feature", table_name="usage_meters")
    op.drop_table("usage_meters")
    op.drop_index("ix_subscription_payments_invoice_status", table_name="subscription_payments")
    op.drop_table("subscription_payments")
    op.drop_index("ix_subscription_invoices_subscription_status", table_name="subscription_invoices")
    op.drop_index("ix_subscription_invoices_tenant_status", table_name="subscription_invoices")
    op.drop_table("subscription_invoices")
