"""Allow legacy orders to use stateless tracking tokens."""

import sqlalchemy as sa
from alembic import op

revision = "0014_tracking_hash_compat"
down_revision = "0013_order_tracking_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "orders",
        "tracking_token_hash",
        existing_type=sa.String(length=64),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "orders",
        "tracking_token_hash",
        existing_type=sa.String(length=64),
        nullable=False,
    )
