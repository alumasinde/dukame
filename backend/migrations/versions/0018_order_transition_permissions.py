"""Bind order workflow transitions to granular permissions."""

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0018_order_transition_permissions"
down_revision = "0017_payment_method_types"
branch_labels = None
depends_on = None

PERMISSIONS = (
    ("orders.confirm", "Confirm orders"),
    ("orders.cancel", "Cancel orders"),
    ("orders.process", "Process orders"),
    ("orders.ready", "Mark orders ready"),
    ("orders.complete", "Complete orders"),
    ("orders.history.read", "View order history"),
    ("orders.export", "Export orders"),
)

TRANSITION_PERMISSIONS = {
    ("pending", "confirmed"): "orders.confirm",
    ("pending", "cancelled"): "orders.cancel",
    ("confirmed", "processing"): "orders.process",
    ("confirmed", "cancelled"): "orders.cancel",
    ("processing", "ready"): "orders.ready",
    ("processing", "cancelled"): "orders.cancel",
    ("ready", "completed"): "orders.complete",
}


def upgrade() -> None:
    bind = op.get_bind()

    permission_table = sa.table(
        "permissions",
        sa.column("id", sa.BigInteger),
        sa.column("public_id", sa.String(32)),
        sa.column("key", sa.String(150)),
        sa.column("name", sa.String(150)),
    )

    for key, name in PERMISSIONS:
        exists = bind.execute(
            sa.select(permission_table.c.id).where(permission_table.c.key == key)
        ).scalar()
        if exists is None:
            op.bulk_insert(
                permission_table,
                [{"public_id": uuid.uuid4().hex, "key": key, "name": name}],
            )

    op.add_column(
        "order_status_transitions",
        sa.Column("permission_id", sa.BigInteger(), nullable=True),
    )

    status_table = sa.table(
        "order_statuses",
        sa.column("id", sa.BigInteger),
        sa.column("code", sa.String(64)),
    )
    transition_table = sa.table(
        "order_status_transitions",
        sa.column("id", sa.BigInteger),
        sa.column("from_status_id", sa.BigInteger),
        sa.column("to_status_id", sa.BigInteger),
        sa.column("permission_id", sa.BigInteger),
    )

    status_codes = {
        row.id: row.code
        for row in bind.execute(sa.select(status_table.c.id, status_table.c.code)).fetchall()
    }
    permission_ids = {
        row.key: row.id
        for row in bind.execute(sa.select(permission_table.c.id, permission_table.c.key)).fetchall()
    }

    for row in bind.execute(
        sa.select(
            transition_table.c.id,
            transition_table.c.from_status_id,
            transition_table.c.to_status_id,
        )
    ).fetchall():
        permission_key = TRANSITION_PERMISSIONS.get(
            (status_codes.get(row.from_status_id), status_codes.get(row.to_status_id))
        )
        if permission_key is None:
            raise RuntimeError(
                f"No permission mapping for order transition {status_codes.get(row.from_status_id)!r} -> {status_codes.get(row.to_status_id)!r}"
            )
        bind.execute(
            sa.update(transition_table)
            .where(transition_table.c.id == row.id)
            .values(permission_id=permission_ids[permission_key])
        )

    op.alter_column(
        "order_status_transitions",
        "permission_id",
        existing_type=sa.BigInteger(),
        nullable=False,
    )
    op.create_foreign_key(
        "fk_order_status_transitions_permission",
        "order_status_transitions",
        "permissions",
        ["permission_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_order_status_transitions_permission",
        "order_status_transitions",
        ["permission_id"],
    )

    roles = sa.table(
        "tenant_roles",
        sa.column("id", sa.BigInteger),
        sa.column("slug", sa.String(100)),
    )
    role_permissions = sa.table(
        "tenant_role_permissions",
        sa.column("role_id", sa.BigInteger),
        sa.column("permission_id", sa.BigInteger),
    )

    operational_keys = [
        "orders.confirm",
        "orders.cancel",
        "orders.process",
        "orders.ready",
        "orders.complete",
        "orders.history.read",
        "orders.export",
    ]
    for role in bind.execute(sa.select(roles.c.id, roles.c.slug)).fetchall():
        if role.slug not in {"owner", "admin", "manager"}:
            continue
        for key in operational_keys:
            permission_id = permission_ids[key]
            exists = bind.execute(
                sa.select(role_permissions.c.role_id).where(
                    role_permissions.c.role_id == role.id,
                    role_permissions.c.permission_id == permission_id,
                )
            ).first()
            if exists is None:
                bind.execute(
                    sa.insert(role_permissions).values(
                        role_id=role.id,
                        permission_id=permission_id,
                    )
                )

    status_manage_id = bind.execute(
        sa.select(permission_table.c.id).where(permission_table.c.key == "orders.status.manage")
    ).scalar()
    if status_manage_id is not None:
        bind.execute(
            sa.delete(role_permissions).where(
                role_permissions.c.permission_id == status_manage_id,
                role_permissions.c.role_id.in_(
                    sa.select(roles.c.id).where(roles.c.slug.in_("owner", "admin", "manager"))
                ),
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    permission_table = sa.table(
        "permissions",
        sa.column("id", sa.BigInteger),
        sa.column("key", sa.String(150)),
    )
    role_permissions = sa.table(
        "tenant_role_permissions",
        sa.column("role_id", sa.BigInteger),
        sa.column("permission_id", sa.BigInteger),
    )

    keys = [key for key, _ in PERMISSIONS]
    permission_ids = list(
        bind.execute(
            sa.select(permission_table.c.id).where(permission_table.c.key.in_(keys))
        ).scalars()
    )
    if permission_ids:
        bind.execute(
            sa.delete(role_permissions).where(
                role_permissions.c.permission_id.in_(permission_ids)
            )
        )

    op.drop_index(
        "ix_order_status_transitions_permission",
        table_name="order_status_transitions",
    )
    op.drop_constraint(
        "fk_order_status_transitions_permission",
        "order_status_transitions",
        type_="foreignkey",
    )
    op.drop_column("order_status_transitions", "permission_id")

    if permission_ids:
        bind.execute(
            sa.delete(permission_table).where(permission_table.c.id.in_(permission_ids))
        )
