"""Add vote_history and job tables, contact voter fields.

Revision ID: add_voter_import
Revises: add_lov_and_pronouns
Create Date: 2025-12-05 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = 'add_voter_import'
down_revision: Union[str, None] = 'add_lov_and_pronouns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create job table first (vote_history references it)
    op.create_table(
        'job',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenant.id'), nullable=False, index=True),
        sa.Column('job_type', sa.String(), nullable=False, index=True),
        sa.Column('status', sa.String(), nullable=False, server_default='pending', index=True),

        # File info
        sa.Column('original_filename', sa.String(), nullable=True),
        sa.Column('file_path', sa.String(), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('total_rows', sa.Integer(), nullable=True),

        # AI mappings
        sa.Column('detected_headers', JSONB(), nullable=True),
        sa.Column('suggested_mappings', JSONB(), nullable=True),
        sa.Column('confirmed_mappings', JSONB(), nullable=True),

        # Matching strategy
        sa.Column('matching_strategy', sa.String(), nullable=True),
        sa.Column('suggested_matching_strategy', sa.String(), nullable=True),
        sa.Column('matching_strategy_reason', sa.Text(), nullable=True),

        # Progress
        sa.Column('rows_processed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rows_created', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rows_updated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rows_skipped', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rows_errored', sa.Integer(), nullable=False, server_default='0'),

        # Errors
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', JSONB(), nullable=True),

        # Timing
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),

        # Owner
        sa.Column('created_by_id', UUID(as_uuid=True), sa.ForeignKey('user.id'), nullable=False, index=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create vote_history table
    op.create_table(
        'vote_history',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenant.id'), nullable=False, index=True),
        sa.Column('contact_id', UUID(as_uuid=True), sa.ForeignKey('contact.id'), nullable=False, index=True),
        sa.Column('election_name', sa.String(), nullable=False, index=True),
        sa.Column('election_date', sa.Date(), nullable=False, index=True),
        sa.Column('election_type', sa.String(), nullable=False, index=True),
        sa.Column('voted', sa.Boolean(), nullable=True),
        sa.Column('voting_method', sa.String(), nullable=True),
        sa.Column('primary_party_voted', sa.String(), nullable=True),

        # Import tracking
        sa.Column('job_id', UUID(as_uuid=True), sa.ForeignKey('job.id'), nullable=True, index=True),
        sa.Column('source_file_name', sa.String(), nullable=True),
        sa.Column('imported_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),

        # Unique constraint
        sa.UniqueConstraint('contact_id', 'election_date', 'election_type', name='uq_vote_history_contact_election'),
    )

    # Add new voter-related columns to contact table
    op.add_column('contact', sa.Column('state_voter_id', sa.String(), nullable=True))
    op.add_column('contact', sa.Column('precinct', sa.String(), nullable=True))
    op.add_column('contact', sa.Column('school_district', sa.String(), nullable=True))
    op.add_column('contact', sa.Column('municipal_district', sa.String(), nullable=True))
    op.add_column('contact', sa.Column('modeled_party', sa.String(), nullable=True))

    # Create indexes for voter fields
    op.create_index('idx_contact_state_voter_id', 'contact', ['state_voter_id'])
    op.create_index('idx_contact_precinct', 'contact', ['precinct'])
    op.create_index('idx_contact_school_district', 'contact', ['school_district'])
    op.create_index('idx_contact_municipal_district', 'contact', ['municipal_district'])

    # Create composite indexes for common queries
    op.create_index('idx_vote_history_contact_date', 'vote_history', ['contact_id', 'election_date'])
    op.create_index('idx_job_tenant_type_status', 'job', ['tenant_id', 'job_type', 'status'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_job_tenant_type_status', table_name='job')
    op.drop_index('idx_vote_history_contact_date', table_name='vote_history')
    op.drop_index('idx_contact_municipal_district', table_name='contact')
    op.drop_index('idx_contact_school_district', table_name='contact')
    op.drop_index('idx_contact_precinct', table_name='contact')
    op.drop_index('idx_contact_state_voter_id', table_name='contact')

    # Drop new contact columns
    op.drop_column('contact', 'modeled_party')
    op.drop_column('contact', 'municipal_district')
    op.drop_column('contact', 'school_district')
    op.drop_column('contact', 'precinct')
    op.drop_column('contact', 'state_voter_id')

    # Drop tables
    op.drop_table('vote_history')
    op.drop_table('job')
