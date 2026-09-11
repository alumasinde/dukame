"""Add card as a store payment method."""

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0016_card_payment_method"
down_revision = "0015_payment_flow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    stores = bind.execute(sa.text("SELECT id FROM stores")).fetchall()
    payment_methods = sa.table(
        "payment_methods",
        sa.column("public_id", sa.String(32)),
        sa.column("store_id", sa.BigInteger),
        sa.column("code", sa.String(32)),
        sa.column("name", sa.String(100)),
        sa.column("is_enabled", sa.Boolean),
        sa.column("sort_order", sa.Integer),
        sa.column("instructions", sa.Text),
    )
    for store in stores:
        exists = bind.execute(
            sa.select(payment_methods.c.public_id).where(
                payment_methods.c.store_id == store[0],
                payment_methods.c.code == "card",
            )
        ).scalar()
        if exists is None:
            bind.execute(
                sa.insert(payment_methods).values(
                    public_id=uuid.uuid4().hex,
                    store_id=store[0],
                    code="card",
                    name="Card",
                    is_enabled=True,
                    sort_order=30,
                    instructions="Accept card payments using your card terminal or configured card processor.",
                )
            )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM payment_methods WHERE code = 'card'"))
