"""Add ARQ tracking fields to job table.

Revision ID: add_job_arq_fields
Revises: add_job_create_unmatched
Create Date: 2025-12-05 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_job_arq_fields'
down_revision: Union[str, None] = 'add_job_create_unmatched'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add ARQ job tracking fields
    op.add_column(
        'job',
        sa.Column('arq_job_id', sa.String(), nullable=True)
    )
    op.add_column(
        'job',
        sa.Column('queued_at', sa.DateTime(), nullable=True)
    )

    # Create index on arq_job_id for efficient lookups
    op.create_index('ix_job_arq_job_id', 'job', ['arq_job_id'])


def downgrade() -> None:
    op.drop_index('ix_job_arq_job_id', table_name='job')
    op.drop_column('job', 'queued_at')
    op.drop_column('job', 'arq_job_id')
