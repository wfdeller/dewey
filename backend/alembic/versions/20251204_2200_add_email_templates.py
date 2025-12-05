"""add email templates and configuration tables

Revision ID: add_email_templates
Revises: add_form_links
Create Date: 2025-12-04 22:00:00.000000+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'add_email_templates'
down_revision: str | None = 'add_form_links'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Email Template table
    op.create_table('email_template',
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('subject', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('body_html', sa.Text(), nullable=False),
        sa.Column('body_text', sa.Text(), nullable=True),
        sa.Column('design_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('default_form_id', sa.Uuid(), nullable=True),
        sa.Column('form_link_single_use', sa.Boolean(), nullable=False),
        sa.Column('form_link_expires_days', sa.Integer(), nullable=True),
        sa.Column('attachments', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('send_count', sa.Integer(), nullable=False),
        sa.Column('last_sent_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['default_form_id'], ['form.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_template_name'), 'email_template', ['name'], unique=False)
    op.create_index(op.f('ix_email_template_tenant_id'), 'email_template', ['tenant_id'], unique=False)

    # Tenant Email Config table
    op.create_table('tenant_email_config',
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('provider', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('from_email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('from_name', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('reply_to_email', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('max_sends_per_hour', sa.Integer(), nullable=False),
        sa.Column('sends_this_hour', sa.Integer(), nullable=False),
        sa.Column('hour_window_start', sa.DateTime(), nullable=True),
        sa.Column('last_send_at', sa.DateTime(), nullable=True),
        sa.Column('last_error', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id')
    )
    op.create_index(op.f('ix_tenant_email_config_tenant_id'), 'tenant_email_config', ['tenant_id'], unique=True)

    # Sent Email log table
    op.create_table('sent_email',
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('template_id', sa.Uuid(), nullable=True),
        sa.Column('to_email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('to_name', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('contact_id', sa.Uuid(), nullable=True),
        sa.Column('subject', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('body_html', sa.Text(), nullable=False),
        sa.Column('body_text', sa.Text(), nullable=True),
        sa.Column('triggered_by', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('workflow_id', sa.Uuid(), nullable=True),
        sa.Column('workflow_execution_id', sa.Uuid(), nullable=True),
        sa.Column('message_id', sa.Uuid(), nullable=True),
        sa.Column('form_submission_id', sa.Uuid(), nullable=True),
        sa.Column('form_link_id', sa.Uuid(), nullable=True),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('provider_message_id', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('error_message', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('opened_at', sa.DateTime(), nullable=True),
        sa.Column('clicked_at', sa.DateTime(), nullable=True),
        sa.Column('bounced_at', sa.DateTime(), nullable=True),
        sa.Column('unsubscribed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['contact_id'], ['contact.id'], ),
        sa.ForeignKeyConstraint(['form_link_id'], ['form_link.id'], ),
        sa.ForeignKeyConstraint(['form_submission_id'], ['form_submission.id'], ),
        sa.ForeignKeyConstraint(['message_id'], ['message.id'], ),
        sa.ForeignKeyConstraint(['template_id'], ['email_template.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ),
        sa.ForeignKeyConstraint(['workflow_execution_id'], ['workflow_execution.id'], ),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflow.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sent_email_contact_id'), 'sent_email', ['contact_id'], unique=False)
    op.create_index(op.f('ix_sent_email_status'), 'sent_email', ['status'], unique=False)
    op.create_index(op.f('ix_sent_email_template_id'), 'sent_email', ['template_id'], unique=False)
    op.create_index(op.f('ix_sent_email_tenant_id'), 'sent_email', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_sent_email_to_email'), 'sent_email', ['to_email'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_sent_email_to_email'), table_name='sent_email')
    op.drop_index(op.f('ix_sent_email_tenant_id'), table_name='sent_email')
    op.drop_index(op.f('ix_sent_email_template_id'), table_name='sent_email')
    op.drop_index(op.f('ix_sent_email_status'), table_name='sent_email')
    op.drop_index(op.f('ix_sent_email_contact_id'), table_name='sent_email')
    op.drop_table('sent_email')
    op.drop_index(op.f('ix_tenant_email_config_tenant_id'), table_name='tenant_email_config')
    op.drop_table('tenant_email_config')
    op.drop_index(op.f('ix_email_template_tenant_id'), table_name='email_template')
    op.drop_index(op.f('ix_email_template_name'), table_name='email_template')
    op.drop_table('email_template')
