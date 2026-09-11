"""Make email NOT NULL

Revision ID: 0009_email_not_null
Revises: 0008_product_media
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = '0009_email_not_null'
down_revision: Union[str, Sequence[str], None] = '0008_product_media'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('users', 'email',
               existing_type=mysql.VARCHAR(charset='utf8mb4', collation='utf8mb4_unicode_ci', length=255),
               nullable=False)


def downgrade() -> None:
    op.alter_column('users', 'email',
               existing_type=mysql.VARCHAR(charset='utf8mb4', collation='utf8mb4_unicode_ci', length=255),
               nullable=True)
