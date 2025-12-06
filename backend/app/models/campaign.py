"""Outbound email marketing campaign models."""

from datetime import datetime
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from sqlalchemy import Column, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.base import TenantBaseModel, BaseModel

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.email import EmailTemplate, SentEmail
    from app.models.contact import Contact
    from app.models.user import User


# Campaign status types
CampaignStatus = Literal[
    "draft",      # Being created/edited
    "scheduled",  # Scheduled for future send
    "active",     # Currently sending
    "paused",     # Temporarily paused
    "completed",  # All sends finished
    "cancelled",  # Stopped before completion
]

CampaignType = Literal["standard", "ab_test", "automated"]

# Recipient status types
RecipientStatus = Literal[
    "pending",      # Not yet queued
    "queued",       # In send queue
    "sent",         # Sent to provider
    "delivered",    # Confirmed delivery
    "opened",       # Email opened
    "clicked",      # Link clicked
    "bounced",      # Bounced (hard or soft)
    "failed",       # Send failed
    "unsubscribed", # Recipient unsubscribed
]


class CampaignBase(SQLModel):
    """Campaign base schema for request/response."""

    name: str = Field(index=True)
    description: str | None = Field(default=None, sa_column=Column(Text))
    campaign_type: str = Field(default="standard")  # standard, ab_test, automated


class Campaign(CampaignBase, TenantBaseModel, table=True):
    """Outbound email marketing campaign."""

    __tablename__ = "campaign"

    # Template configuration
    template_id: UUID = Field(foreign_key="email_template.id", index=True)

    # A/B Testing (optional)
    variant_b_template_id: UUID | None = Field(
        default=None, foreign_key="email_template.id"
    )
    ab_test_split: int = Field(default=50)  # Percentage for variant A (0-100)
    ab_test_winner_metric: str | None = Field(default=None)  # "opens", "clicks"
    ab_test_winner_selected_at: datetime | None = Field(default=None)
    ab_test_winning_variant: str | None = Field(default=None)  # "a" or "b"

    # Status and scheduling
    status: str = Field(default="draft", index=True)
    scheduled_at: datetime | None = Field(default=None, index=True)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    paused_at: datetime | None = Field(default=None)

    # Recipient selection criteria (stored as filter configuration)
    recipient_filter: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    # Structure: {
    #   "mode": "filter" | "manual",
    #   "tags": ["vip", "donor"],
    #   "tag_match": "any" | "all",
    #   "categories": [{"id": "uuid", "stance": "supports"}],
    #   "category_match": "any" | "all",
    #   "custom_fields": [{"field_id": "uuid", "operator": "eq", "value": "..."}],
    #   "states": ["CA", "NY"],
    #   "zip_codes": ["90210", "10001"],
    #   "party_affiliations": ["democrat"],
    #   "has_email": true,
    #   "exclude_suppressed": true,  # Always true by default
    #   "manual_contact_ids": ["uuid1", "uuid2"]  # For manual mode
    # }

    # Sending configuration
    send_rate_per_hour: int | None = Field(default=None)  # Override tenant rate limit
    from_email_override: str | None = Field(default=None)
    from_name_override: str | None = Field(default=None)
    reply_to_override: str | None = Field(default=None)

    # Aggregated statistics (denormalized for performance)
    total_recipients: int = Field(default=0)
    total_sent: int = Field(default=0)
    total_delivered: int = Field(default=0)
    total_opened: int = Field(default=0)
    total_clicked: int = Field(default=0)
    total_bounced: int = Field(default=0)
    total_unsubscribed: int = Field(default=0)
    total_failed: int = Field(default=0)

    # Unique metrics (deduplicated - each contact counted once)
    unique_opens: int = Field(default=0)
    unique_clicks: int = Field(default=0)

    # Created by
    created_by_id: UUID | None = Field(default=None, foreign_key="user.id", index=True)

    # Job tracking (for ARQ)
    job_id: UUID | None = Field(default=None, foreign_key="job.id", index=True)

    # Relationships
    tenant: "Tenant" = Relationship(back_populates="campaigns")
    recipients: list["CampaignRecipient"] = Relationship(
        back_populates="campaign",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class CampaignRecipient(BaseModel, table=True):
    """Individual recipient tracking for a campaign."""

    __tablename__ = "campaign_recipient"
    __table_args__ = (
        UniqueConstraint("campaign_id", "contact_id", name="uq_campaign_recipient"),
    )

    campaign_id: UUID = Field(foreign_key="campaign.id", index=True)
    contact_id: UUID = Field(foreign_key="contact.id", index=True)

    # Email address at time of send (cached in case contact email changes)
    email: str = Field(index=True)

    # A/B test assignment
    variant: str | None = Field(default=None)  # "a" or "b" for A/B tests

    # Delivery status
    status: str = Field(default="pending", index=True)
    # pending, queued, sent, delivered, opened, clicked, bounced, failed, unsubscribed

    # Sent email reference
    sent_email_id: UUID | None = Field(default=None, foreign_key="sent_email.id")

    # Timing
    queued_at: datetime | None = Field(default=None)
    sent_at: datetime | None = Field(default=None)
    delivered_at: datetime | None = Field(default=None)
    opened_at: datetime | None = Field(default=None)
    clicked_at: datetime | None = Field(default=None)
    bounced_at: datetime | None = Field(default=None)
    failed_at: datetime | None = Field(default=None)
    unsubscribed_at: datetime | None = Field(default=None)

    # Error tracking
    error_message: str | None = Field(default=None, sa_column=Column(Text))
    bounce_type: str | None = Field(default=None)  # "hard", "soft"

    # Open/click counts (for multiple opens/clicks)
    open_count: int = Field(default=0)
    click_count: int = Field(default=0)

    # Relationships
    campaign: Campaign = Relationship(back_populates="recipients")
    contact: "Contact" = Relationship()
    sent_email: "SentEmail" = Relationship()


# ============================================================================
# Pydantic Schemas for API
# ============================================================================


class CampaignCreate(CampaignBase):
    """Schema for creating a campaign draft."""

    template_id: UUID
    variant_b_template_id: UUID | None = None
    ab_test_split: int = 50
    recipient_filter: dict = {}
    send_rate_per_hour: int | None = None
    from_email_override: str | None = None
    from_name_override: str | None = None
    reply_to_override: str | None = None


class CampaignUpdate(SQLModel):
    """Schema for updating a campaign (draft/scheduled only)."""

    name: str | None = None
    description: str | None = None
    template_id: UUID | None = None
    variant_b_template_id: UUID | None = None
    ab_test_split: int | None = None
    recipient_filter: dict | None = None
    scheduled_at: datetime | None = None
    send_rate_per_hour: int | None = None
    from_email_override: str | None = None
    from_name_override: str | None = None
    reply_to_override: str | None = None


class CampaignRead(CampaignBase):
    """Schema for reading a campaign."""

    id: UUID
    tenant_id: UUID
    template_id: UUID
    variant_b_template_id: UUID | None
    ab_test_split: int
    status: str
    scheduled_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None

    # Stats
    total_recipients: int
    total_sent: int
    total_delivered: int
    total_opened: int
    total_clicked: int
    total_bounced: int
    total_unsubscribed: int
    unique_opens: int
    unique_clicks: int

    created_at: datetime
    updated_at: datetime


class CampaignDetail(CampaignRead):
    """Extended schema with full details."""

    recipient_filter: dict
    send_rate_per_hour: int | None
    from_email_override: str | None
    from_name_override: str | None
    reply_to_override: str | None
    paused_at: datetime | None
    ab_test_winner_metric: str | None
    ab_test_winning_variant: str | None
    created_by_id: UUID | None
    job_id: UUID | None


class CampaignRecipientRead(SQLModel):
    """Schema for reading a campaign recipient."""

    id: UUID
    campaign_id: UUID
    contact_id: UUID
    email: str
    variant: str | None
    status: str
    sent_at: datetime | None
    opened_at: datetime | None
    clicked_at: datetime | None
    bounced_at: datetime | None
    open_count: int
    click_count: int
    error_message: str | None


class RecipientFilterPreview(SQLModel):
    """Schema for recipient filter preview response."""

    total_count: int
    sample_contacts: list[dict]  # First 10 contacts


class CampaignAnalytics(SQLModel):
    """Schema for campaign analytics response."""

    campaign_id: UUID
    status: str

    # Counts
    total_recipients: int
    total_sent: int
    total_delivered: int
    total_opened: int
    total_clicked: int
    total_bounced: int
    total_unsubscribed: int
    total_failed: int

    # Rates (percentages)
    delivery_rate: float
    open_rate: float
    click_rate: float
    bounce_rate: float
    unsubscribe_rate: float

    # Unique metrics
    unique_opens: int
    unique_clicks: int
    unique_open_rate: float
    unique_click_rate: float

    # A/B test results (if applicable)
    ab_test_results: dict | None = None

    # Timeline data (hourly/daily aggregates)
    timeline: list[dict] | None = None
