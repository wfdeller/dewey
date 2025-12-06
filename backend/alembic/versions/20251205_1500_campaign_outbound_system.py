"""Campaign system transformation: inbound detection to outbound marketing.

This migration transforms the Campaign table from inbound message detection
to outbound email marketing. Key changes:

1. Rename existing campaign table to legacy_campaign_detection (preserve history)
2. Create new campaign table with outbound marketing fields
3. Create campaign_recipient table for per-contact tracking
4. Create email_suppression table for bounces/unsubscribes
5. Create campaign_recommendation table for AI suggestions
6. Update message table: remove campaign_id, add coordinated detection fields
7. Add campaign_id to sent_email for tracking

Revision ID: campaign_outbound_system
Revises: make_contact_email_nullable
Create Date: 2025-12-05 15:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "campaign_outbound_system"
down_revision: Union[str, None] = "make_contact_email_nullable"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # Step 1: Drop indexes on existing campaign table before rename
    # (these indexes will conflict with new campaign table indexes)
    # =========================================================================
    # Use if_exists to handle partial migrations
    op.execute("DROP INDEX IF EXISTS ix_campaign_tenant_id")
    op.execute("DROP INDEX IF EXISTS ix_campaign_name")
    op.execute("DROP INDEX IF EXISTS ix_campaign_template_hash")

    # =========================================================================
    # Step 2: Rename existing campaign table to preserve legacy data
    # =========================================================================
    op.rename_table("campaign", "legacy_campaign_detection")

    # =========================================================================
    # Step 2: Create new campaign table (outbound marketing)
    # =========================================================================
    op.create_table(
        "campaign",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        # Core fields
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("campaign_type", sa.String(), nullable=False, server_default="standard"),
        # Template configuration
        sa.Column("template_id", sa.UUID(), nullable=False),
        sa.Column("variant_b_template_id", sa.UUID(), nullable=True),
        sa.Column("ab_test_split", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("ab_test_winner_metric", sa.String(), nullable=True),
        sa.Column("ab_test_winner_selected_at", sa.DateTime(), nullable=True),
        sa.Column("ab_test_winning_variant", sa.String(), nullable=True),
        # Status and scheduling
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("scheduled_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("paused_at", sa.DateTime(), nullable=True),
        # Recipient selection
        sa.Column("recipient_filter", postgresql.JSONB(), nullable=False, server_default="{}"),
        # Sending configuration
        sa.Column("send_rate_per_hour", sa.Integer(), nullable=True),
        sa.Column("from_email_override", sa.String(), nullable=True),
        sa.Column("from_name_override", sa.String(), nullable=True),
        sa.Column("reply_to_override", sa.String(), nullable=True),
        # Aggregated statistics
        sa.Column("total_recipients", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_delivered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_opened", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_clicked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_bounced", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_unsubscribed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_opens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_clicks", sa.Integer(), nullable=False, server_default="0"),
        # Created by and job tracking
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("job_id", sa.UUID(), nullable=True),
        # Primary key and foreign keys
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["email_template.id"]),
        sa.ForeignKeyConstraint(["variant_b_template_id"], ["email_template.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["job.id"]),
    )
    op.create_index("ix_campaign_tenant_id", "campaign", ["tenant_id"])
    op.create_index("ix_campaign_name", "campaign", ["name"])
    op.create_index("ix_campaign_status", "campaign", ["status"])
    op.create_index("ix_campaign_scheduled_at", "campaign", ["scheduled_at"])
    op.create_index("ix_campaign_template_id", "campaign", ["template_id"])
    op.create_index("ix_campaign_created_by_id", "campaign", ["created_by_id"])
    op.create_index("ix_campaign_job_id", "campaign", ["job_id"])

    # =========================================================================
    # Step 3: Create campaign_recipient table
    # =========================================================================
    op.create_table(
        "campaign_recipient",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        # Foreign keys
        sa.Column("campaign_id", sa.UUID(), nullable=False),
        sa.Column("contact_id", sa.UUID(), nullable=False),
        # Email cached at send time
        sa.Column("email", sa.String(), nullable=False),
        # A/B test assignment
        sa.Column("variant", sa.String(), nullable=True),
        # Delivery status
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("sent_email_id", sa.UUID(), nullable=True),
        # Timing
        sa.Column("queued_at", sa.DateTime(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("opened_at", sa.DateTime(), nullable=True),
        sa.Column("clicked_at", sa.DateTime(), nullable=True),
        sa.Column("bounced_at", sa.DateTime(), nullable=True),
        sa.Column("failed_at", sa.DateTime(), nullable=True),
        sa.Column("unsubscribed_at", sa.DateTime(), nullable=True),
        # Error tracking
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("bounce_type", sa.String(), nullable=True),
        # Counts
        sa.Column("open_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("click_count", sa.Integer(), nullable=False, server_default="0"),
        # Primary key and constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaign.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["contact.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sent_email_id"], ["sent_email.id"]),
        sa.UniqueConstraint("campaign_id", "contact_id", name="uq_campaign_recipient"),
    )
    op.create_index("ix_campaign_recipient_campaign_id", "campaign_recipient", ["campaign_id"])
    op.create_index("ix_campaign_recipient_contact_id", "campaign_recipient", ["contact_id"])
    op.create_index("ix_campaign_recipient_email", "campaign_recipient", ["email"])
    op.create_index("ix_campaign_recipient_status", "campaign_recipient", ["status"])

    # =========================================================================
    # Step 4: Create email_suppression table
    # =========================================================================
    op.create_table(
        "email_suppression",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        # Suppressed email
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("contact_id", sa.UUID(), nullable=True),
        # Suppression type
        sa.Column("suppression_type", sa.String(), nullable=False),
        # Scope
        sa.Column("is_global", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("campaign_id", sa.UUID(), nullable=True),
        # Source tracking
        sa.Column("source_campaign_id", sa.UUID(), nullable=True),
        sa.Column("source_sent_email_id", sa.UUID(), nullable=True),
        # When suppressed
        sa.Column("suppressed_at", sa.DateTime(), nullable=False),
        # Provider info
        sa.Column("provider_info", postgresql.JSONB(), nullable=True),
        # Removal tracking
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("removed_at", sa.DateTime(), nullable=True),
        sa.Column("removed_by_id", sa.UUID(), nullable=True),
        sa.Column("removal_reason", sa.Text(), nullable=True),
        # Primary key and foreign keys
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["contact.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaign.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_campaign_id"], ["campaign.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_sent_email_id"], ["sent_email.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["removed_by_id"], ["user.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_email_suppression_tenant_id", "email_suppression", ["tenant_id"])
    op.create_index("ix_email_suppression_email", "email_suppression", ["email"])
    op.create_index("ix_email_suppression_contact_id", "email_suppression", ["contact_id"])
    op.create_index("ix_email_suppression_suppression_type", "email_suppression", ["suppression_type"])
    op.create_index("ix_email_suppression_campaign_id", "email_suppression", ["campaign_id"])
    op.create_index("ix_email_suppression_is_active", "email_suppression", ["is_active"])

    # =========================================================================
    # Step 5: Create campaign_recommendation table
    # =========================================================================
    op.create_table(
        "campaign_recommendation",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        # Trigger
        sa.Column("trigger_type", sa.String(), nullable=False),
        sa.Column("category_id", sa.UUID(), nullable=True),
        sa.Column("topic_keywords", postgresql.JSONB(), nullable=False, server_default="[]"),
        # Trend data
        sa.Column("trend_data", postgresql.JSONB(), nullable=False, server_default="{}"),
        # Recommendation details
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("suggested_audience_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("suggested_filter", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("suggested_subject_lines", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("suggested_talking_points", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.5"),
        # Status
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        # Dismissal tracking
        sa.Column("dismissed_at", sa.DateTime(), nullable=True),
        sa.Column("dismissed_by_id", sa.UUID(), nullable=True),
        sa.Column("dismissal_reason", sa.String(), nullable=True),
        # Conversion tracking
        sa.Column("converted_campaign_id", sa.UUID(), nullable=True),
        sa.Column("converted_at", sa.DateTime(), nullable=True),
        sa.Column("converted_by_id", sa.UUID(), nullable=True),
        # Expiration
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        # Primary key and foreign keys
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["category.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["dismissed_by_id"], ["user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["converted_campaign_id"], ["campaign.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["converted_by_id"], ["user.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_campaign_recommendation_tenant_id", "campaign_recommendation", ["tenant_id"])
    op.create_index("ix_campaign_recommendation_trigger_type", "campaign_recommendation", ["trigger_type"])
    op.create_index("ix_campaign_recommendation_category_id", "campaign_recommendation", ["category_id"])
    op.create_index("ix_campaign_recommendation_status", "campaign_recommendation", ["status"])
    op.create_index("ix_campaign_recommendation_title", "campaign_recommendation", ["title"])
    op.create_index("ix_campaign_recommendation_expires_at", "campaign_recommendation", ["expires_at"])
    op.create_index("ix_campaign_recommendation_converted_campaign_id", "campaign_recommendation", ["converted_campaign_id"])

    # =========================================================================
    # Step 6: Update message table - add coordinated detection fields
    # =========================================================================
    # Add new coordinated detection fields
    op.add_column("message", sa.Column("is_coordinated", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("message", sa.Column("coordinated_group_id", sa.String(), nullable=True))
    op.add_column("message", sa.Column("coordinated_confidence", sa.Float(), nullable=True))
    op.add_column("message", sa.Column("coordinated_source_org", sa.String(), nullable=True))

    # Create indexes for new fields
    op.create_index("ix_message_is_coordinated", "message", ["is_coordinated"])
    op.create_index("ix_message_coordinated_group_id", "message", ["coordinated_group_id"])

    # Migrate data from old fields to new fields
    op.execute("""
        UPDATE message
        SET is_coordinated = is_template_match,
            coordinated_confidence = template_similarity_score
        WHERE is_template_match = true
    """)

    # Drop old fields and campaign_id FK
    op.drop_constraint("message_campaign_id_fkey", "message", type_="foreignkey")
    op.drop_index("ix_message_campaign_id", "message")
    op.drop_index("ix_message_is_template_match", "message")
    op.drop_column("message", "campaign_id")
    op.drop_column("message", "is_template_match")
    op.drop_column("message", "template_similarity_score")

    # =========================================================================
    # Step 7: Add campaign_id to sent_email for tracking
    # =========================================================================
    op.add_column("sent_email", sa.Column("campaign_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "sent_email_campaign_id_fkey",
        "sent_email",
        "campaign",
        ["campaign_id"],
        ["id"],
        ondelete="SET NULL"
    )
    op.create_index("ix_sent_email_campaign_id", "sent_email", ["campaign_id"])


def downgrade() -> None:
    # =========================================================================
    # Step 7: Remove campaign_id from sent_email
    # =========================================================================
    op.drop_index("ix_sent_email_campaign_id", "sent_email")
    op.drop_constraint("sent_email_campaign_id_fkey", "sent_email", type_="foreignkey")
    op.drop_column("sent_email", "campaign_id")

    # =========================================================================
    # Step 6: Restore message table to old schema
    # =========================================================================
    # Add back old fields
    op.add_column("message", sa.Column("campaign_id", sa.UUID(), nullable=True))
    op.add_column("message", sa.Column("is_template_match", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("message", sa.Column("template_similarity_score", sa.Float(), nullable=True))

    # Migrate data back
    op.execute("""
        UPDATE message
        SET is_template_match = is_coordinated,
            template_similarity_score = coordinated_confidence
        WHERE is_coordinated = true
    """)

    # Create indexes and FK for old fields
    op.create_index("ix_message_is_template_match", "message", ["is_template_match"])
    op.create_index("ix_message_campaign_id", "message", ["campaign_id"])
    op.create_foreign_key(
        "message_campaign_id_fkey",
        "message",
        "legacy_campaign_detection",  # Points to renamed table
        ["campaign_id"],
        ["id"],
        ondelete="SET NULL"
    )

    # Drop new coordinated fields
    op.drop_index("ix_message_coordinated_group_id", "message")
    op.drop_index("ix_message_is_coordinated", "message")
    op.drop_column("message", "coordinated_source_org")
    op.drop_column("message", "coordinated_confidence")
    op.drop_column("message", "coordinated_group_id")
    op.drop_column("message", "is_coordinated")

    # =========================================================================
    # Step 5: Drop campaign_recommendation table
    # =========================================================================
    op.drop_index("ix_campaign_recommendation_converted_campaign_id", "campaign_recommendation")
    op.drop_index("ix_campaign_recommendation_expires_at", "campaign_recommendation")
    op.drop_index("ix_campaign_recommendation_title", "campaign_recommendation")
    op.drop_index("ix_campaign_recommendation_status", "campaign_recommendation")
    op.drop_index("ix_campaign_recommendation_category_id", "campaign_recommendation")
    op.drop_index("ix_campaign_recommendation_trigger_type", "campaign_recommendation")
    op.drop_index("ix_campaign_recommendation_tenant_id", "campaign_recommendation")
    op.drop_table("campaign_recommendation")

    # =========================================================================
    # Step 4: Drop email_suppression table
    # =========================================================================
    op.drop_index("ix_email_suppression_is_active", "email_suppression")
    op.drop_index("ix_email_suppression_campaign_id", "email_suppression")
    op.drop_index("ix_email_suppression_suppression_type", "email_suppression")
    op.drop_index("ix_email_suppression_contact_id", "email_suppression")
    op.drop_index("ix_email_suppression_email", "email_suppression")
    op.drop_index("ix_email_suppression_tenant_id", "email_suppression")
    op.drop_table("email_suppression")

    # =========================================================================
    # Step 3: Drop campaign_recipient table
    # =========================================================================
    op.drop_index("ix_campaign_recipient_status", "campaign_recipient")
    op.drop_index("ix_campaign_recipient_email", "campaign_recipient")
    op.drop_index("ix_campaign_recipient_contact_id", "campaign_recipient")
    op.drop_index("ix_campaign_recipient_campaign_id", "campaign_recipient")
    op.drop_table("campaign_recipient")

    # =========================================================================
    # Step 2: Drop new campaign table
    # =========================================================================
    op.drop_index("ix_campaign_job_id", "campaign")
    op.drop_index("ix_campaign_created_by_id", "campaign")
    op.drop_index("ix_campaign_template_id", "campaign")
    op.drop_index("ix_campaign_scheduled_at", "campaign")
    op.drop_index("ix_campaign_status", "campaign")
    op.drop_index("ix_campaign_name", "campaign")
    op.drop_index("ix_campaign_tenant_id", "campaign")
    op.drop_table("campaign")

    # =========================================================================
    # Step 1: Rename legacy table back to campaign
    # =========================================================================
    op.rename_table("legacy_campaign_detection", "campaign")
