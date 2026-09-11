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

PERMISSION_KEY = "orders.status.manage"


def upgrade() -> None:
    bind = op.get_bind()

    permission_table = sa.table(
        "permissions",
        sa.column("id", sa.BigInteger),
        sa.column("public_id", sa.String(32)),
        sa.column("key", sa.String(150)),
        sa.column("name", sa.String(150)),
    )

    existing = bind.execute(
        sa.select(permission_table.c.id).where(permission_table.c.key == PERMISSION_KEY)
    ).first()
    if existing is None:
        op.bulk_insert(
            permission_table,
            [{
                "public_id": uuid.uuid4().hex,
                "key": PERMISSION_KEY,
                "name": "Change order status",
            }],
        )

    permission_id = bind.execute(
        sa.select(permission_table.c.id).where(permission_table.c.key == PERMISSION_KEY)
    ).scalar_one()

    bind.execute(
        sa.text(
            "DELETE FROM tenant_role_permissions "
            "WHERE permission_id = :permission_id"
        ),
        {"permission_id": permission_id},
    )

    bind.execute(
        sa.text(
            "INSERT INTO tenant_role_permissions (role_id, permission_id) "
            "SELECT tr.id, :permission_id FROM tenant_roles AS tr "
            "WHERE tr.slug IN ('owner', 'admin', 'manager') "
            "AND NOT EXISTS ("
            "SELECT 1 FROM tenant_role_permissions AS existing "
            "WHERE existing.role_id = tr.id "
            "AND existing.permission_id = :permission_id"
            ")"
        ),
        {"permission_id": permission_id},
    )

    orders_manage_id = bind.execute(
        sa.select(permission_table.c.id).where(permission_table.c.key == "orders.manage")
    ).scalar()
    if orders_manage_id is not None:
        bind.execute(
            sa.text(
                "DELETE FROM tenant_role_permissions "
                "WHERE permission_id = :permission_id"
            ),
            {"permission_id": orders_manage_id},
        )
        bind.execute(
            sa.text("DELETE FROM permissions WHERE id = :permission_id"),
            {"permission_id": orders_manage_id},
        )

    orders_read_id = bind.execute(
        sa.select(permission_table.c.id).where(permission_table.c.key == "orders.read")
    ).scalar()
    if orders_read_id is not None:
        bind.execute(
            sa.text(
                "INSERT INTO tenant_role_permissions (role_id, permission_id) "
                "SELECT tr.id, :permission_id FROM tenant_roles AS tr "
                "WHERE tr.slug = 'staff' "
                "AND NOT EXISTS ("
                "SELECT 1 FROM tenant_role_permissions AS existing "
                "WHERE existing.role_id = tr.id "
                "AND existing.permission_id = :permission_id"
                ")"
            ),
            {"permission_id": orders_read_id},
        )


def downgrade() -> None:
    bind = op.get_bind()
    permission_table = sa.table(
        "permissions",
        sa.column("id", sa.BigInteger),
        sa.column("public_id", sa.String(32)),
        sa.column("key", sa.String(150)),
        sa.column("name", sa.String(150)),
    )

    permission_id = bind.execute(
        sa.select(permission_table.c.id).where(permission_table.c.key == PERMISSION_KEY)
    ).scalar()
    if permission_id is not None:
        bind.execute(
            sa.text(
                "DELETE FROM tenant_role_permissions "
                "WHERE permission_id = :permission_id"
            ),
            {"permission_id": permission_id},
        )
        bind.execute(
            sa.text("DELETE FROM permissions WHERE id = :permission_id"),
            {"permission_id": permission_id},
        )

    orders_manage_id = bind.execute(
        sa.select(permission_table.c.id).where(permission_table.c.key == "orders.manage")
    ).scalar()
    if orders_manage_id is None:
        op.bulk_insert(
            permission_table,
            [{
                "public_id": uuid.uuid4().hex,
                "key": "orders.manage",
                "name": "Manage orders",
            }],
        )
        orders_manage_id = bind.execute(
            sa.select(permission_table.c.id).where(permission_table.c.key == "orders.manage")
        ).scalar_one()

    bind.execute(
        sa.text(
            "INSERT INTO tenant_role_permissions (role_id, permission_id) "
            "SELECT tr.id, :permission_id FROM tenant_roles AS tr "
            "WHERE tr.slug IN ('owner', 'admin') "
            "AND NOT EXISTS ("
            "SELECT 1 FROM tenant_role_permissions AS existing "
            "WHERE existing.role_id = tr.id "
            "AND existing.permission_id = :permission_id"
            ")"
        ),
        {"permission_id": orders_manage_id},
    )
