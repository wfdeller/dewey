"""Add contact is_active and inactive_reason fields.

Revision ID: add_contact_is_active
Revises: add_contact_demographics
Create Date: 2025-12-05 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_contact_is_active'
down_revision: Union[str, None] = 'add_contact_demographics'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_active field (defaults to True for existing contacts)
    op.add_column('contact', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('contact', sa.Column('inactive_reason', sa.String(), nullable=True))

    # Create index for filtering active/inactive contacts
    op.create_index('idx_contact_is_active', 'contact', ['is_active'])


def downgrade() -> None:
    op.drop_index('idx_contact_is_active', table_name='contact')
    op.drop_column('contact', 'inactive_reason')
    op.drop_column('contact', 'is_active')
