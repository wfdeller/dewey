"""Add list_of_values table and contact pronouns field.

Revision ID: add_lov_and_pronouns
Revises: add_contact_is_active
Create Date: 2025-12-05 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'add_lov_and_pronouns'
down_revision: Union[str, None] = 'add_contact_is_active'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create list_of_values table
    op.create_table(
        'list_of_values',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenant.id'), nullable=False, index=True),
        sa.Column('list_type', sa.String(), nullable=False, index=True),
        sa.Column('value', sa.String(), nullable=False, index=True),
        sa.Column('label', sa.String(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('tenant_id', 'list_type', 'value', name='uq_lov_tenant_type_value'),
    )

    # Create index for common queries
    op.create_index('idx_lov_tenant_list_type', 'list_of_values', ['tenant_id', 'list_type'])

    # Add pronouns field to contact table
    op.add_column('contact', sa.Column('pronouns', sa.String(), nullable=True))


def downgrade() -> None:
    # Remove pronouns from contact
    op.drop_column('contact', 'pronouns')

    # Drop list_of_values table
    op.drop_index('idx_lov_tenant_list_type', table_name='list_of_values')
    op.drop_table('list_of_values')
