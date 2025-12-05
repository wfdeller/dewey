"""add tone and stance system - replace sentiment

Revision ID: add_tone_stance
Revises: add_email_templates
Create Date: 2025-12-04 23:00:00.000000+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'add_tone_stance'
down_revision: str | None = 'add_email_templates'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add tones column to analysis table (JSONB array)
    op.add_column('analysis', sa.Column('tones', postgresql.JSONB(), server_default='[]', nullable=True))

    # Make existing sentiment columns nullable for migration period
    op.alter_column('analysis', 'sentiment_score', existing_type=sa.Float(), nullable=True)
    op.alter_column('analysis', 'sentiment_label', existing_type=sa.String(), nullable=True)
    op.alter_column('analysis', 'sentiment_confidence', existing_type=sa.Float(), nullable=True)

    # Add GIN index for efficient tone queries
    op.execute("CREATE INDEX IF NOT EXISTS idx_analysis_tones ON analysis USING GIN (tones)")

    # Add stance columns to message_category table
    op.add_column('message_category', sa.Column('stance', sa.String(), nullable=True))
    op.add_column('message_category', sa.Column('stance_confidence', sa.Float(), nullable=True))

    # Add dominant_tones column to contact table
    op.add_column('contact', sa.Column('dominant_tones', postgresql.ARRAY(sa.String()), server_default='{}', nullable=True))


def downgrade() -> None:
    # Remove dominant_tones from contact
    op.drop_column('contact', 'dominant_tones')

    # Remove stance columns from message_category
    op.drop_column('message_category', 'stance_confidence')
    op.drop_column('message_category', 'stance')

    # Remove tones index and column from analysis
    op.execute("DROP INDEX IF EXISTS idx_analysis_tones")
    op.drop_column('analysis', 'tones')

    # Restore non-nullable sentiment columns (if data allows)
    # Note: This may fail if there are NULL values
    op.alter_column('analysis', 'sentiment_score', existing_type=sa.Float(), nullable=False)
    op.alter_column('analysis', 'sentiment_label', existing_type=sa.String(), nullable=False)
    op.alter_column('analysis', 'sentiment_confidence', existing_type=sa.Float(), nullable=False)
