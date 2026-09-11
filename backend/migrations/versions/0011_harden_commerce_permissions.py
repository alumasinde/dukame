"""harden commerce permissions

Revision ID: 0011_harden_commerce_permissions
Revises: 0010_carts_orders
"""
import uuid

import sqlalchemy as sa
from alembic import op

revision = "0011_harden_commerce_permissions"
down_revision = "0010_carts_orders"
branch_labels = None
depends_on = None

PERMISSIONS = (("orders.status.manage", "Change order status"),)


def upgrade() -> None:
    permission_table = sa.table(
        "permissions",
        sa.column("public_id", sa.String),
        sa.column("key", sa.String),
        sa.column("name", sa.String),
    )
    op.bulk_insert(permission_table, [{"public_id": uuid.uuid4().hex, "key": key, "name": name} for key, name in PERMISSIONS])
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM tenant_role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE key = 'orders.manage')"))
    bind.execute(sa.text("INSERT INTO tenant_role_permissions (role_id, permission_id) SELECT tr.id, p.id FROM tenant_roles tr CROSS JOIN permissions p WHERE tr.slug IN ('owner', 'admin', 'manager') AND p.key = 'orders.status.manage'"))
    bind.execute(sa.text("INSERT INTO tenant_role_permissions (role_id, permission_id) SELECT tr.id, p.id FROM tenant_roles tr CROSS JOIN permissions p WHERE tr.slug = 'staff' AND p.key = 'orders.read' AND NOT EXISTS (SELECT 1 FROM tenant_role_permissions trp WHERE trp.role_id = tr.id AND trp.permission_id = p.id)"))
    bind.execute(sa.text("DELETE FROM permissions WHERE key = 'orders.manage'"))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM tenant_role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE key = 'orders.status.manage')"))
    bind.execute(sa.text("DELETE FROM permissions WHERE key = 'orders.status.manage'"))
    bind.execute(sa.text("INSERT INTO permissions (public_id, key, name) VALUES (:public_id, 'orders.manage', 'Manage orders')"), {"public_id": uuid.uuid4().hex})
    bind.execute(sa.text("INSERT INTO tenant_role_permissions (role_id, permission_id) SELECT tr.id, p.id FROM tenant_roles tr CROSS JOIN permissions p WHERE tr.slug IN ('owner', 'admin') AND p.key = 'orders.manage'"))
