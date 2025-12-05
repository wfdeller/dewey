"""Add create_unmatched column to job table.

Revision ID: add_job_create_unmatched
Revises: add_audit_log
Create Date: 2025-12-05 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_job_create_unmatched'
down_revision: Union[str, None] = 'add_audit_log'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'job',
        sa.Column('create_unmatched', sa.Boolean(), nullable=False, server_default='true')
    )


def downgrade() -> None:
    op.drop_column('job', 'create_unmatched')
