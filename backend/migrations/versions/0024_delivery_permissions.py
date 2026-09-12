"""Add granular delivery permissions."""

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0024_delivery_permissions"
down_revision = "0023_order_delivery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table(
        "permissions",
        sa.column("id", sa.BigInteger),
        sa.column("public_id", sa.String(32)),
        sa.column("key", sa.String(150)),
        sa.column("name", sa.String(150)),
    )
    for key, name in {
        "delivery.assign": "Assign deliveries",
        "delivery.otp.issue": "Issue delivery OTP",
        "delivery.confirm": "Confirm delivery",
    }.items():
        exists = bind.execute(sa.select(permissions.c.id).where(permissions.c.key == key)).scalar()
        if exists is None:
            bind.execute(permissions.insert().values(public_id=uuid.uuid4().hex, key=key, name=name))

    roles = sa.table("tenant_roles", sa.column("id", sa.BigInteger), sa.column("slug", sa.String(100)))
    role_permissions = sa.table("tenant_role_permissions", sa.column("role_id", sa.BigInteger), sa.column("permission_id", sa.BigInteger))
    permission_ids = dict(bind.execute(sa.select(permissions.c.key, permissions.c.id).where(permissions.c.key.in_(["delivery.assign", "delivery.otp.issue", "delivery.confirm"]))).all())
    for role in bind.execute(sa.select(roles.c.id, roles.c.slug)).fetchall():
        if role.slug not in {"owner", "admin", "manager"}:
            continue
        for permission_id in permission_ids.values():
            if bind.execute(sa.select(role_permissions.c.role_id).where(role_permissions.c.role_id == role.id, role_permissions.c.permission_id == permission_id)).first() is None:
                bind.execute(role_permissions.insert().values(role_id=role.id, permission_id=permission_id))


def downgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table("permissions", sa.column("id", sa.BigInteger), sa.column("key", sa.String(150)))
    role_permissions = sa.table("tenant_role_permissions", sa.column("role_id", sa.BigInteger), sa.column("permission_id", sa.BigInteger))
    rows = bind.execute(sa.select(permissions.c.id).where(permissions.c.key.in_(["delivery.assign", "delivery.otp.issue", "delivery.confirm"]))).fetchall()
    for row in rows:
        bind.execute(role_permissions.delete().where(role_permissions.c.permission_id == row.id))
        bind.execute(permissions.delete().where(permissions.c.id == row.id))
