"""AI-driven campaign recommendations based on message trends."""

from datetime import datetime
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.base import TenantBaseModel

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.category import Category
    from app.models.campaign import Campaign
    from app.models.user import User


# Recommendation trigger types
RecommendationTrigger = Literal[
    "trending_topic",     # Category/topic with significant increase
    "sentiment_shift",    # Notable sentiment change in category
    "engagement_spike",   # High engagement on specific topic
    "seasonal",           # Time-based/recurring patterns
]

# Recommendation status
RecommendationStatus = Literal["active", "dismissed", "converted", "expired"]


class CampaignRecommendation(TenantBaseModel, table=True):
    """AI-generated campaign recommendation based on message analysis.

    The system analyzes incoming message trends to suggest outbound campaigns
    targeting contacts who have shown interest in trending topics.
    """

    __tablename__ = "campaign_recommendation"

    # What triggered this recommendation
    trigger_type: str = Field(index=True)  # trending_topic, sentiment_shift, engagement_spike, seasonal

    # Related category/topic (optional)
    category_id: UUID | None = Field(default=None, foreign_key="category.id", index=True)

    # Topic keywords for non-category-based recommendations
    topic_keywords: list[str] = Field(default_factory=list, sa_column=Column(JSONB))

    # Trend data that triggered the recommendation
    trend_data: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    # Structure: {
    #   "period": "7_days" | "30_days",
    #   "current_count": 234,
    #   "previous_count": 167,
    #   "change_percent": 40.1,
    #   "stance_breakdown": {"supports": 180, "opposes": 54},
    #   "sentiment_avg": 0.65,
    #   "sentiment_change": 0.15,
    #   "sample_message_ids": ["uuid1", "uuid2", "uuid3"]
    # }

    # Recommendation details
    title: str = Field(index=True)  # "Global warming interest is up 40% this month"
    description: str = Field(sa_column=Column(Text))
    suggested_audience_size: int = Field(default=0)

    # Pre-built filter for easy campaign creation
    suggested_filter: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    # Structure matches Campaign.recipient_filter

    # AI-generated content suggestions
    suggested_subject_lines: list[str] = Field(default_factory=list, sa_column=Column(JSONB))
    suggested_talking_points: list[str] = Field(default_factory=list, sa_column=Column(JSONB))

    # Priority/confidence score (0.0 - 1.0)
    confidence_score: float = Field(default=0.5)

    # Status tracking
    status: str = Field(default="active", index=True)  # active, dismissed, converted, expired

    # Dismissal tracking
    dismissed_at: datetime | None = Field(default=None)
    dismissed_by_id: UUID | None = Field(default=None, foreign_key="user.id")
    dismissal_reason: str | None = Field(default=None)

    # Conversion tracking (when recommendation becomes a campaign)
    converted_campaign_id: UUID | None = Field(default=None, foreign_key="campaign.id", index=True)
    converted_at: datetime | None = Field(default=None)
    converted_by_id: UUID | None = Field(default=None, foreign_key="user.id")

    # Expiration
    expires_at: datetime | None = Field(default=None, index=True)

    # Relationships
    tenant: "Tenant" = Relationship()
    category: "Category" = Relationship()
    converted_campaign: "Campaign" = Relationship()


# ============================================================================
# Pydantic Schemas for API
# ============================================================================


class CampaignRecommendationRead(SQLModel):
    """Schema for reading a campaign recommendation."""

    id: UUID
    tenant_id: UUID
    trigger_type: str
    category_id: UUID | None
    topic_keywords: list[str]
    trend_data: dict
    title: str
    description: str
    suggested_audience_size: int
    suggested_filter: dict
    suggested_subject_lines: list[str]
    suggested_talking_points: list[str]
    confidence_score: float
    status: str
    expires_at: datetime | None
    created_at: datetime


class CampaignRecommendationDetail(CampaignRecommendationRead):
    """Extended schema with all details."""

    dismissed_at: datetime | None
    dismissed_by_id: UUID | None
    dismissal_reason: str | None
    converted_campaign_id: UUID | None
    converted_at: datetime | None
    converted_by_id: UUID | None


class CampaignRecommendationDismiss(SQLModel):
    """Schema for dismissing a recommendation."""

    reason: str | None = None


class CampaignRecommendationConvert(SQLModel):
    """Schema for converting a recommendation to a campaign."""

    name: str  # Campaign name
    template_id: UUID  # Template to use
    use_suggested_filter: bool = True  # Use the suggested filter or provide custom
    custom_filter: dict | None = None  # Custom filter if not using suggested
