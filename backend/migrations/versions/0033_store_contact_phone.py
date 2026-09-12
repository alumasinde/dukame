"""Add optional public contact phone for storefront trust / WhatsApp CTA."""

import sqlalchemy as sa
from alembic import op

revision = "0033_store_contact_phone"
down_revision = "0032_subscription_billing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "stores",
        sa.Column("contact_phone", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("stores", "contact_phone")
