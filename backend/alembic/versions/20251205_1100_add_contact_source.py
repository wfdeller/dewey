"""Add source tracking fields to contact.

Revision ID: add_contact_source
Revises: add_voter_import
Create Date: 2025-12-05 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_contact_source'
down_revision: Union[str, None] = 'add_voter_import'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add source tracking fields to contact table
    # index=True in Field() creates ix_contact_source automatically
    op.add_column('contact', sa.Column('source', sa.String(), nullable=True))
    op.add_column('contact', sa.Column('source_detail', sa.String(), nullable=True))

    # Create index for source column (if not exists)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_contact_source ON contact (source)
    """)


def downgrade() -> None:
    op.drop_index('ix_contact_source', table_name='contact', if_exists=True)
    op.drop_column('contact', 'source_detail')
    op.drop_column('contact', 'source')
