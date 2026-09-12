"""add_delivery_fields_to_orders

Revision ID: 76065ef8370d
Revises: 0034_stock_reservations
Create Date: 2026-09-12 20:06:00.302100
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0035_add_delivery'
down_revision: Union[str, Sequence[str], None] = '0034_stock_reservations'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add delivery fields to orders table
    # First add as nullable to handle existing orders
    op.add_column('orders', sa.Column('delivery_address', sa.String(length=500), nullable=True))
    op.add_column('orders', sa.Column('delivery_landmark', sa.String(length=500), nullable=True))
    op.add_column('orders', sa.Column('delivery_notes', sa.String(length=1000), nullable=True))
    op.add_column('orders', sa.Column('delivery_option', sa.String(length=50), nullable=True, server_default='standard'))
    
    # Update existing orders with default values
    op.execute("UPDATE orders SET delivery_address = 'Store pickup', delivery_option = 'pickup' WHERE delivery_address IS NULL")
    
    # Now make the required fields non-nullable
    op.alter_column('orders', 'delivery_address', nullable=False)
    op.alter_column('orders', 'delivery_option', nullable=False)


def downgrade() -> None:
    op.drop_column('orders', 'delivery_option')
    op.drop_column('orders', 'delivery_notes')
    op.drop_column('orders', 'delivery_landmark')
    op.drop_column('orders', 'delivery_address')
