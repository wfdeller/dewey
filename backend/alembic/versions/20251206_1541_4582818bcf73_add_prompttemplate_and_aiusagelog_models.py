"""Add PromptTemplate and AIUsageLog models

Revision ID: 4582818bcf73
Revises: campaign_outbound_system
Create Date: 2025-12-06 15:41:11.255463+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4582818bcf73"
down_revision: str | None = "campaign_outbound_system"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create prompt_template table
    op.create_table(
        "prompt_template",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("user_prompt_template", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("previous_version_id", sa.Uuid(), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("max_tokens", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["previous_version_id"],
            ["prompt_template.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_prompt_template_name"), "prompt_template", ["name"], unique=False
    )
    op.create_index(
        op.f("ix_prompt_template_tenant_id"),
        "prompt_template",
        ["tenant_id"],
        unique=False,
    )

    # Create ai_usage_log table
    op.create_table(
        "ai_usage_log",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column(
            "operation_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column("operation_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("ai_provider", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("ai_model", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("prompt_template_id", sa.Uuid(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=True),
        sa.Column("processing_time_ms", sa.Integer(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("error_message", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["prompt_template_id"],
            ["prompt_template.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ai_usage_log_ai_provider"),
        "ai_usage_log",
        ["ai_provider"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_usage_log_operation_type"),
        "ai_usage_log",
        ["operation_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_usage_log_tenant_id"), "ai_usage_log", ["tenant_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_usage_log_tenant_id"), table_name="ai_usage_log")
    op.drop_index(op.f("ix_ai_usage_log_operation_type"), table_name="ai_usage_log")
    op.drop_index(op.f("ix_ai_usage_log_ai_provider"), table_name="ai_usage_log")
    op.drop_table("ai_usage_log")
    op.drop_index(op.f("ix_prompt_template_tenant_id"), table_name="prompt_template")
    op.drop_index(op.f("ix_prompt_template_name"), table_name="prompt_template")
    op.drop_table("prompt_template")
