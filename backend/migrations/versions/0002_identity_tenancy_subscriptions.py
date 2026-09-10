"""identity, tenancy and subscription foundations

Revision ID: 0002_identity_tenancy_subscriptions
Revises: 0001_identity
"""
import uuid

from alembic import op
import sqlalchemy as sa

revision = "0002_identity_tenancy_subscriptions"
down_revision = "0001_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tenant_users", sa.Column("role", sa.String(length=64), nullable=False, server_default="member"))
    op.add_column("tenant_users", sa.Column("status", sa.String(length=32), nullable=False, server_default="active"))
    op.create_index("ix_tenant_users_tenant_status", "tenant_users", ["tenant_id", "status"])

    op.create_table("auth_sessions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("public_id"), sa.UniqueConstraint("refresh_token_hash"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), mysql_engine="InnoDB")
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])

    op.create_table("plans",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False), sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False), sa.Column("description", sa.Text(), nullable=True),
        sa.Column("monthly_price_minor", sa.Integer(), server_default="0", nullable=False),
        sa.Column("quarterly_price_minor", sa.Integer(), server_default="0", nullable=False),
        sa.Column("yearly_price_minor", sa.Integer(), server_default="0", nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="KES", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("public_id"), sa.UniqueConstraint("slug"), mysql_engine="InnoDB")

    op.create_table("plan_features",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False), sa.Column("plan_id", sa.BigInteger(), nullable=False),
        sa.Column("feature_key", sa.String(length=100), nullable=False), sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("plan_id", "feature_key", name="uq_plan_features_plan_key"),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="CASCADE"), mysql_engine="InnoDB")
    op.create_index("ix_plan_features_key", "plan_features", ["feature_key"])

    op.create_table("subscriptions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False), sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False), sa.Column("plan_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("billing_interval", sa.String(length=16), server_default="monthly", nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False), sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), server_default="0", nullable=False), sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("public_id"), sa.UniqueConstraint("tenant_id", name="uq_subscriptions_tenant"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="RESTRICT"), mysql_engine="InnoDB")
    op.create_index("ix_subscriptions_status_period", "subscriptions", ["status", "current_period_end"])

    op.create_table("subscription_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False), sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("subscription_id", sa.BigInteger(), nullable=False), sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("public_id"), sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"], ondelete="CASCADE"), mysql_engine="InnoDB")
    op.create_index("ix_subscription_events_subscription_created", "subscription_events", ["subscription_id", "created_at"])

    plans = sa.table("plans", sa.column("public_id", sa.String), sa.column("slug", sa.String), sa.column("name", sa.String), sa.column("description", sa.Text), sa.column("monthly_price_minor", sa.Integer), sa.column("quarterly_price_minor", sa.Integer), sa.column("yearly_price_minor", sa.Integer), sa.column("currency", sa.String), sa.column("is_active", sa.Boolean))
    op.bulk_insert(plans, [{"public_id": uuid.uuid4().hex, "slug": "free", "name": "Free", "description": "Starter plan", "monthly_price_minor": 0, "quarterly_price_minor": 0, "yearly_price_minor": 0, "currency": "KES", "is_active": True}])


def downgrade() -> None:
    op.drop_index("ix_subscription_events_subscription_created", table_name="subscription_events")
    op.drop_table("subscription_events")
    op.drop_index("ix_subscriptions_status_period", table_name="subscriptions")
    op.drop_table("subscriptions")
    op.drop_index("ix_plan_features_key", table_name="plan_features")
    op.drop_table("plan_features")
    op.drop_table("plans")
    op.drop_index("ix_auth_sessions_expires_at", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_user_id", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_index("ix_tenant_users_tenant_status", table_name="tenant_users")
    op.drop_column("tenant_users", "status")
    op.drop_column("tenant_users", "role")
    op.drop_column("users", "last_login_at")
