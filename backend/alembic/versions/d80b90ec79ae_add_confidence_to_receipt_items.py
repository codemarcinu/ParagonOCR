"""Add confidence to receipt_items

Revision ID: d80b90ec79ae
Revises: 2fa51550de33
Create Date: 2026-01-06 09:52:34.877711

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd80b90ec79ae'
down_revision: Union[str, None] = '2fa51550de33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('receipt_items', sa.Column('confidence', sa.Numeric(3, 2), nullable=True, server_default='1.0'))


def downgrade() -> None:
    op.drop_column('receipt_items', 'confidence')

