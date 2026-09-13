"""add_delivery_fields_to_orders

Revision ID: 0035_add_delivery
Revises: 0034_stock_reservations
Create Date: 2026-09-12 20:06:00.302100
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0035_add_delivery"
down_revision: Union[str, Sequence[str], None] = "0034_stock_reservations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add delivery fields as nullable first.
    op.add_column(
        "orders",
        sa.Column("delivery_address", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("delivery_landmark", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("delivery_notes", sa.String(length=1000), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column(
            "delivery_option",
            sa.String(length=50),
            nullable=True,
            server_default="standard",
        ),
    )

    # Fill defaults for any existing orders.
    op.execute(
        """
        UPDATE orders
        SET delivery_address = 'Store pickup',
            delivery_option = 'pickup'
        WHERE delivery_address IS NULL
        """
    )

    # Make required fields non-nullable.
    op.alter_column(
        "orders",
        "delivery_address",
        existing_type=sa.String(length=500),
        nullable=False,
    )
    op.alter_column(
        "orders",
        "delivery_option",
        existing_type=sa.String(length=50),
        nullable=False,
        existing_server_default="standard",
    )


def downgrade() -> None:
    op.drop_column("orders", "delivery_option")
    op.drop_column("orders", "delivery_notes")
    op.drop_column("orders", "delivery_landmark")
    op.drop_column("orders", "delivery_address")