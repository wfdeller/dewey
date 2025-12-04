"""Message model for incoming communications."""

from datetime import datetime
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.base import TenantBaseModel

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.contact import Contact
    from app.models.campaign import Campaign
    from app.models.analysis import Analysis
    from app.models.category import MessageCategory
    from app.models.workflow import WorkflowExecution


MessageSource = Literal["email", "form", "api", "upload"]
ProcessingStatus = Literal["pending", "processing", "completed", "failed"]


class MessageBase(SQLModel):
    """Message base schema."""

    subject: str = Field(max_length=500)
    body_text: str = Field(sa_column=Column(Text))
    body_html: str | None = Field(default=None, sa_column=Column(Text))
    sender_email: str = Field(index=True)
    sender_name: str | None = None
    source: str = Field(default="api")  # email, form, api, upload


class Message(MessageBase, TenantBaseModel, table=True):
    """Message database model."""

    __tablename__ = "message"

    # Foreign keys
    contact_id: UUID | None = Field(default=None, foreign_key="contact.id", index=True)
    campaign_id: UUID | None = Field(default=None, foreign_key="campaign.id", index=True)

    # External reference
    external_id: str | None = Field(default=None, index=True)  # Original message ID

    # Processing status
    processing_status: str = Field(default="pending", index=True)  # pending, processing, completed, failed
    received_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    processed_at: datetime | None = Field(default=None)

    # Campaign/template detection
    is_template_match: bool = Field(default=False, index=True)
    template_similarity_score: float | None = Field(default=None)

    # Attachments stored as JSON array
    attachments: list[dict] = Field(default_factory=list, sa_column=Column(JSONB))

    # Source metadata (varies by source type)
    source_metadata: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    # For email: headers, message_id, in_reply_to, references, received_chain,
    #            spf_result, dkim_result, dmarc_result
    # For form/API: ip_address, geolocation, user_agent, browser, os,
    #              device_type, referrer_url, utm_source, utm_medium,
    #              utm_campaign, session_id, fingerprint_hash

    # Relationships
    tenant: "Tenant" = Relationship(back_populates="messages")
    contact: "Contact" = Relationship(back_populates="messages")
    campaign: "Campaign" = Relationship(back_populates="messages")
    analysis: "Analysis" = Relationship(back_populates="message")
    message_categories: list["MessageCategory"] = Relationship(back_populates="message")
    workflow_executions: list["WorkflowExecution"] = Relationship(back_populates="message")


class MessageCreate(MessageBase):
    """Schema for creating a message."""

    attachments: list[dict] | None = None
    source_metadata: dict | None = None


class MessageRead(MessageBase):
    """Schema for reading a message."""

    id: UUID
    tenant_id: UUID
    contact_id: UUID | None
    campaign_id: UUID | None
    processing_status: ProcessingStatus
    is_template_match: bool
    template_similarity_score: float | None
    received_at: datetime
    processed_at: datetime | None


class MessageUpdate(SQLModel):
    """Schema for updating a message."""

    processing_status: ProcessingStatus | None = None
    contact_id: UUID | None = None
