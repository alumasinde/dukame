"""Require references for order inventory movements."""

from alembic import op

revision = "0025_inventory_order_reference_integrity"
down_revision = "0024_delivery_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_inventory_movements_order_reference",
        "inventory_movements",
        "movement_type NOT IN ('sale', 'return') OR (reference_type IS NOT NULL AND reference_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_inventory_movements_order_reference", "inventory_movements", type_="check")
