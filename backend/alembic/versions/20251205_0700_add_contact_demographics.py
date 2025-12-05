"""Add contact demographic and geographic fields.

Revision ID: add_contact_demographics
Revises: add_tone_stance
Create Date: 2025-12-05 07:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_contact_demographics'
down_revision: Union[str, None] = 'add_tone_stance'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Demographics
    op.add_column('contact', sa.Column('date_of_birth', sa.Date(), nullable=True))
    op.add_column('contact', sa.Column('age_estimate', sa.Integer(), nullable=True))
    op.add_column('contact', sa.Column('age_estimate_source', sa.String(), nullable=True))
    op.add_column('contact', sa.Column('gender', sa.String(), nullable=True))

    # Name components
    op.add_column('contact', sa.Column('prefix', sa.String(), nullable=True))
    op.add_column('contact', sa.Column('first_name', sa.String(), nullable=True))
    op.add_column('contact', sa.Column('middle_name', sa.String(), nullable=True))
    op.add_column('contact', sa.Column('last_name', sa.String(), nullable=True))
    op.add_column('contact', sa.Column('suffix', sa.String(), nullable=True))
    op.add_column('contact', sa.Column('preferred_name', sa.String(), nullable=True))

    # Professional/occupational
    op.add_column('contact', sa.Column('occupation', sa.String(), nullable=True))
    op.add_column('contact', sa.Column('employer', sa.String(), nullable=True))
    op.add_column('contact', sa.Column('job_title', sa.String(), nullable=True))
    op.add_column('contact', sa.Column('industry', sa.String(), nullable=True))

    # Voter/political info
    op.add_column('contact', sa.Column('voter_status', sa.String(), nullable=True))
    op.add_column('contact', sa.Column('party_affiliation', sa.String(), nullable=True))
    op.add_column('contact', sa.Column('voter_registration_date', sa.Date(), nullable=True))

    # Socioeconomic indicators
    op.add_column('contact', sa.Column('income_bracket', sa.String(), nullable=True))
    op.add_column('contact', sa.Column('education_level', sa.String(), nullable=True))
    op.add_column('contact', sa.Column('homeowner_status', sa.String(), nullable=True))

    # Household info
    op.add_column('contact', sa.Column('household_size', sa.Integer(), nullable=True))
    op.add_column('contact', sa.Column('has_children', sa.Boolean(), nullable=True))
    op.add_column('contact', sa.Column('marital_status', sa.String(), nullable=True))

    # Language/communication preferences
    op.add_column('contact', sa.Column('preferred_language', sa.String(), nullable=True))
    op.add_column('contact', sa.Column('communication_preference', sa.String(), nullable=True))

    # Additional contact methods
    op.add_column('contact', sa.Column('secondary_email', sa.String(), nullable=True))
    op.add_column('contact', sa.Column('mobile_phone', sa.String(), nullable=True))
    op.add_column('contact', sa.Column('work_phone', sa.String(), nullable=True))

    # Geographic targeting (denormalized for efficient queries)
    op.add_column('contact', sa.Column('state', sa.String(), nullable=True))
    op.add_column('contact', sa.Column('zip_code', sa.String(), nullable=True))
    op.add_column('contact', sa.Column('county', sa.String(), nullable=True))
    op.add_column('contact', sa.Column('congressional_district', sa.String(), nullable=True))
    op.add_column('contact', sa.Column('state_legislative_district', sa.String(), nullable=True))

    # Geolocation
    op.add_column('contact', sa.Column('latitude', sa.Float(), nullable=True))
    op.add_column('contact', sa.Column('longitude', sa.Float(), nullable=True))

    # Create indexes for common filter/search fields
    op.create_index('idx_contact_state', 'contact', ['state'])
    op.create_index('idx_contact_zip_code', 'contact', ['zip_code'])
    op.create_index('idx_contact_county', 'contact', ['county'])
    op.create_index('idx_contact_congressional_district', 'contact', ['congressional_district'])
    op.create_index('idx_contact_state_legislative_district', 'contact', ['state_legislative_district'])
    op.create_index('idx_contact_party_affiliation', 'contact', ['party_affiliation'])
    op.create_index('idx_contact_voter_status', 'contact', ['voter_status'])
    op.create_index('idx_contact_last_name', 'contact', ['last_name'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_contact_last_name', table_name='contact')
    op.drop_index('idx_contact_voter_status', table_name='contact')
    op.drop_index('idx_contact_party_affiliation', table_name='contact')
    op.drop_index('idx_contact_state_legislative_district', table_name='contact')
    op.drop_index('idx_contact_congressional_district', table_name='contact')
    op.drop_index('idx_contact_county', table_name='contact')
    op.drop_index('idx_contact_zip_code', table_name='contact')
    op.drop_index('idx_contact_state', table_name='contact')

    # Drop columns (in reverse order)
    op.drop_column('contact', 'longitude')
    op.drop_column('contact', 'latitude')
    op.drop_column('contact', 'state_legislative_district')
    op.drop_column('contact', 'congressional_district')
    op.drop_column('contact', 'county')
    op.drop_column('contact', 'zip_code')
    op.drop_column('contact', 'state')
    op.drop_column('contact', 'work_phone')
    op.drop_column('contact', 'mobile_phone')
    op.drop_column('contact', 'secondary_email')
    op.drop_column('contact', 'communication_preference')
    op.drop_column('contact', 'preferred_language')
    op.drop_column('contact', 'marital_status')
    op.drop_column('contact', 'has_children')
    op.drop_column('contact', 'household_size')
    op.drop_column('contact', 'homeowner_status')
    op.drop_column('contact', 'education_level')
    op.drop_column('contact', 'income_bracket')
    op.drop_column('contact', 'voter_registration_date')
    op.drop_column('contact', 'party_affiliation')
    op.drop_column('contact', 'voter_status')
    op.drop_column('contact', 'industry')
    op.drop_column('contact', 'job_title')
    op.drop_column('contact', 'employer')
    op.drop_column('contact', 'occupation')
    op.drop_column('contact', 'preferred_name')
    op.drop_column('contact', 'suffix')
    op.drop_column('contact', 'last_name')
    op.drop_column('contact', 'middle_name')
    op.drop_column('contact', 'first_name')
    op.drop_column('contact', 'prefix')
    op.drop_column('contact', 'gender')
    op.drop_column('contact', 'age_estimate_source')
    op.drop_column('contact', 'age_estimate')
    op.drop_column('contact', 'date_of_birth')
