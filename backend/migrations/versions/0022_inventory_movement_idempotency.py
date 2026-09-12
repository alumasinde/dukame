"""Prevent duplicate inventory movements for the same business reference."""

from alembic import op

revision = "0022_inventory_movement_idemp"
down_revision = "0021_inventory_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_inventory_movements_reference_type_id",
        "inventory_movements",
        ["store_id", "reference_type", "reference_id", "movement_type"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_inventory_movements_reference_type_id", "inventory_movements", type_="unique")
