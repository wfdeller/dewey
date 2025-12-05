"""Add audit_log table.

Revision ID: add_audit_log
Revises: add_contact_source
Create Date: 2025-12-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = 'add_audit_log'
down_revision: Union[str, None] = 'add_contact_source'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'audit_log',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenant.id'), nullable=False, index=True),

        # What changed
        sa.Column('entity_type', sa.String(), nullable=False, index=True),
        sa.Column('entity_id', UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('entity_name', sa.String(), nullable=True),

        # What happened
        sa.Column('action', sa.String(), nullable=False, index=True),
        sa.Column('description', sa.Text(), nullable=False),

        # Who did it
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('user.id'), nullable=True, index=True),
        sa.Column('user_email', sa.String(), nullable=True),
        sa.Column('user_name', sa.String(), nullable=True),

        # Context
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),

        # Change details
        sa.Column('changes', JSONB, nullable=True),
        sa.Column('extra_data', JSONB, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create composite index for efficient entity-specific queries
    op.create_index(
        'ix_audit_log_entity',
        'audit_log',
        ['tenant_id', 'entity_type', 'entity_id']
    )

    # Create index for time-based queries
    op.create_index(
        'ix_audit_log_created_at',
        'audit_log',
        ['tenant_id', 'created_at']
    )


def downgrade() -> None:
    op.drop_index('ix_audit_log_created_at', table_name='audit_log')
    op.drop_index('ix_audit_log_entity', table_name='audit_log')
    op.drop_table('audit_log')
