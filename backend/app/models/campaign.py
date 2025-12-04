"""Campaign model for coordinated/template message detection."""

from datetime import datetime
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from sqlalchemy import Column, Text
from sqlmodel import Field, Relationship, SQLModel

from app.models.base import TenantBaseModel

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.message import Message


CampaignStatus = Literal["detected", "confirmed", "dismissed"]
DetectionType = Literal["template", "coordinated", "manual"]


class CampaignBase(SQLModel):
    """Campaign base schema."""

    name: str = Field(index=True)
    status: str = Field(default="detected")  # detected, confirmed, dismissed
    detection_type: str = Field(default="template")  # template, coordinated, manual


class Campaign(CampaignBase, TenantBaseModel, table=True):
    """Campaign database model for template/coordinated message detection."""

    __tablename__ = "campaign"

    # Template detection
    template_hash: str = Field(index=True)  # Normalized content hash
    template_text: str = Field(sa_column=Column(Text))  # Representative sample
    template_subject_pattern: str | None = None  # Regex or exact match

    # Timing
    first_seen_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)

    # Denormalized stats (updated as messages arrive)
    message_count: int = Field(default=1)
    unique_senders: int = Field(default=1)

    # Source identification
    source_organization: str | None = None  # e.g., "Sierra Club", "NRA"

    # Staff notes
    notes: str | None = Field(default=None, sa_column=Column(Text))

    # Relationships
    tenant: "Tenant" = Relationship(back_populates="campaigns")
    messages: list["Message"] = Relationship(back_populates="campaign")


class CampaignCreate(CampaignBase):
    """Schema for creating a campaign (usually automatic)."""

    template_hash: str
    template_text: str
    template_subject_pattern: str | None = None


class CampaignRead(CampaignBase):
    """Schema for reading a campaign."""

    id: UUID
    tenant_id: UUID
    template_subject_pattern: str | None
    first_seen_at: datetime
    last_seen_at: datetime
    message_count: int
    unique_senders: int
    source_organization: str | None


class CampaignUpdate(SQLModel):
    """Schema for updating a campaign."""

    name: str | None = None
    status: CampaignStatus | None = None
    source_organization: str | None = None
    notes: str | None = None


class CampaignDetail(CampaignRead):
    """Extended schema with template preview."""

    template_text: str
    notes: str | None
