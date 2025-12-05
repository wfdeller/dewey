"""add form links table

Revision ID: add_form_links
Revises: 38f06fc31d15
Create Date: 2025-12-04 21:00:00.000000+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'add_form_links'
down_revision: str | None = '38f06fc31d15'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('form_link',
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('form_id', sa.Uuid(), nullable=False),
        sa.Column('contact_id', sa.Uuid(), nullable=False),
        sa.Column('token', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('is_single_use', sa.Boolean(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('use_count', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['contact_id'], ['contact.id'], ),
        sa.ForeignKeyConstraint(['form_id'], ['form.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token')
    )
    op.create_index(op.f('ix_form_link_contact_id'), 'form_link', ['contact_id'], unique=False)
    op.create_index(op.f('ix_form_link_form_id'), 'form_link', ['form_id'], unique=False)
    op.create_index(op.f('ix_form_link_token'), 'form_link', ['token'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_form_link_token'), table_name='form_link')
    op.drop_index(op.f('ix_form_link_form_id'), table_name='form_link')
    op.drop_index(op.f('ix_form_link_contact_id'), table_name='form_link')
    op.drop_table('form_link')
