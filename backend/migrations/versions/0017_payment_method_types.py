"""Allow separate Paybill and Till payment methods per store."""

import sqlalchemy as sa
from alembic import op

revision = "0017_payment_method_types"
down_revision = "0016_card_payment_method"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payment_methods", sa.Column("payment_type", sa.String(length=32), nullable=True))

    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE payment_methods
            SET payment_type = CASE
                WHEN code = 'mpesa' THEN 'stk_push'
                WHEN code = 'mpesa_paybill' THEN 'paybill'
                WHEN code = 'cash' THEN 'cash'
                WHEN code = 'card' THEN 'card'
                ELSE NULL
            END
            """
        )
    )

    op.drop_constraint("uq_payment_methods_store_code", "payment_methods", type_="unique")
    op.create_unique_constraint(
        "uq_payment_methods_store_code_type",
        "payment_methods",
        ["store_id", "code", "payment_type"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_payment_methods_store_code_type", "payment_methods", type_="unique")
    op.create_unique_constraint(
        "uq_payment_methods_store_code",
        "payment_methods",
        ["store_id", "code"],
    )
    op.drop_column("payment_methods", "payment_type")
