"""Add RBAC, account recovery tokens and subscription trials."""
import uuid

import sqlalchemy as sa
from alembic import op

revision = "0003_rbac_recovery"
down_revision = "0002_identity_tenancy_subs"
branch_labels = None
depends_on = None

PERMISSIONS = (
    ("tenant.read", "View shop settings"),
    ("tenant.manage", "Manage shop settings"),
    ("members.read", "View shop members"),
    ("members.manage", "Manage shop members"),
    ("roles.read", "View roles and permissions"),
    ("roles.manage", "Manage roles and permissions"),
    ("subscription.read", "View subscription"),
    ("subscription.manage", "Manage subscription"),
    ("account.read", "View account"),
    ("account.manage", "Manage account"),
)

ROLE_PERMISSIONS = {
    "admin": {p[0] for p in PERMISSIONS if p[0] != "subscription.manage"},
    "manager": {"tenant.read", "members.read", "roles.read", "subscription.read", "account.read"},
    "staff": {"tenant.read", "account.read"},
}


def upgrade() -> None:
    op.add_column("plans", sa.Column("trial_days", sa.Integer(), server_default="0", nullable=False))
    op.create_table(
        "tenant_roles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("is_system", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_tenant_roles_tenant_slug"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_tenant_roles_tenant", "tenant_roles", ["tenant_id"])
    op.create_table(
        "permissions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("key", sa.String(length=150), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("key"),
        mysql_engine="InnoDB",
    )
    op.create_table(
        "tenant_role_permissions",
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.Column("permission_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
        sa.ForeignKeyConstraint(["role_id"], ["tenant_roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        mysql_engine="InnoDB",
    )
    op.create_table(
        "verification_tokens",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("token_hash"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_verification_tokens_user", "verification_tokens", ["user_id"])
    op.create_index("ix_verification_tokens_expires", "verification_tokens", ["expires_at"])
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("token_hash"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_password_reset_tokens_user", "password_reset_tokens", ["user_id"])
    op.create_index("ix_password_reset_tokens_expires", "password_reset_tokens", ["expires_at"])
    op.add_column("tenant_users", sa.Column("role_id", sa.BigInteger(), nullable=True))
    op.create_index("ix_tenant_users_role_id", "tenant_users", ["role_id"])
    op.create_foreign_key("fk_tenant_users_role_id", "tenant_users", "tenant_roles", ["role_id"], ["id"], ondelete="SET NULL")

    permission_table = sa.table("permissions", sa.column("public_id", sa.String()), sa.column("key", sa.String()), sa.column("name", sa.String()))
    op.bulk_insert(permission_table, [{"public_id": uuid.uuid4().hex, "key": key, "name": name} for key, name in PERMISSIONS])
    bind = op.get_bind()
    for name, slug in (("Owner", "owner"), ("Administrator", "admin"), ("Manager", "manager"), ("Staff", "staff")):
        bind.execute(sa.text("INSERT INTO tenant_roles (public_id, tenant_id, name, slug, is_system) SELECT REPLACE(UUID(), '-', ''), id, :name, :slug, 1 FROM tenants"), {"name": name, "slug": slug})
    bind.execute(sa.text("UPDATE tenant_users tu JOIN tenant_roles tr ON tr.tenant_id = tu.tenant_id AND tr.slug = CASE WHEN tu.role IN ('owner','admin','manager','staff') THEN tu.role ELSE 'owner' END SET tu.role_id = tr.id"))
    for slug, keys in ROLE_PERMISSIONS.items():
        bind.execute(sa.text("INSERT INTO tenant_role_permissions (role_id, permission_id) SELECT tr.id, p.id FROM tenant_roles tr JOIN permissions p ON p.key IN (" + ", ".join(f":k{i}" for i in range(len(keys))) + ") WHERE tr.slug = :slug"), {**{f"k{i}": key for i, key in enumerate(keys)}, "slug": slug})
    bind.execute(sa.text("INSERT INTO tenant_role_permissions (role_id, permission_id) SELECT tr.id, p.id FROM tenant_roles tr CROSS JOIN permissions p WHERE tr.slug = 'owner'"))


def downgrade() -> None:
    op.drop_constraint("fk_tenant_users_role_id", "tenant_users", type_="foreignkey")
    op.drop_index("ix_tenant_users_role_id", table_name="tenant_users")
    op.drop_column("tenant_users", "role_id")
    op.drop_index("ix_password_reset_tokens_expires", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_user", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_index("ix_verification_tokens_expires", table_name="verification_tokens")
    op.drop_index("ix_verification_tokens_user", table_name="verification_tokens")
    op.drop_table("verification_tokens")
    op.drop_table("tenant_role_permissions")
    op.drop_index("ix_tenant_roles_tenant", table_name="tenant_roles")
    op.drop_table("tenant_roles")
    op.drop_table("permissions")
    op.drop_column("plans", "trial_days")
