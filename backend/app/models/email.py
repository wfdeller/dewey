"""Email template and configuration models."""

from datetime import datetime
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.base import BaseModel, TenantBaseModel

if TYPE_CHECKING:
    from app.models.tenant import Tenant


# Email provider types
EmailProvider = Literal["smtp", "ses", "graph", "sendgrid"]

# Template variable categories for the UI
TemplateVariableCategory = Literal["contact", "form", "message", "tenant", "custom"]


class EmailTemplateBase(SQLModel):
    """Email template base schema."""

    name: str = Field(index=True)
    description: str | None = Field(default=None)
    subject: str  # Can contain variables like {{contact.name}}

    # Template status
    is_active: bool = Field(default=True)


class EmailTemplate(EmailTemplateBase, TenantBaseModel, table=True):
    """Email template database model.

    Templates support variable substitution using Jinja2 syntax:
    - {{contact.name}}, {{contact.email}}
    - {{form_link}} - Pre-identified form link URL
    - {{form.name}} - Form name for the link
    - {{message.subject}} - Original message subject (for auto-replies)
    - {{tenant.name}} - Organization name
    - {{custom.field_name}} - Custom contact fields
    """

    __tablename__ = "email_template"

    # Template content
    body_html: str = Field(sa_column=Column(Text))  # HTML content with variables
    body_text: str | None = Field(default=None, sa_column=Column(Text))  # Plain text fallback

    # Template design data (for visual editor)
    # Stores the editor's JSON structure for re-editing
    design_json: dict | None = Field(default=None, sa_column=Column(JSONB))
    # Structure example for block-based editor:
    # {
    #   "blocks": [
    #     {"type": "header", "content": "<h1>Hello {{contact.name}}</h1>"},
    #     {"type": "text", "content": "<p>Thank you for...</p>"},
    #     {"type": "button", "url": "{{form_link}}", "text": "Take Survey"},
    #     {"type": "image", "src": "https://...", "alt": "Logo"}
    #   ],
    #   "styles": {"primaryColor": "#1890ff", "fontFamily": "Arial"}
    # }

    # Default form to use for {{form_link}} variable (optional)
    default_form_id: UUID | None = Field(default=None, foreign_key="form.id")

    # Form link options when generating links
    form_link_single_use: bool = Field(default=True)
    form_link_expires_days: int | None = Field(default=7)  # None = no expiration

    # Attachments (stored references, not actual files)
    attachments: list[dict] = Field(default_factory=list, sa_column=Column(JSONB))
    # Structure: [{"name": "logo.png", "url": "https://...", "content_type": "image/png"}]

    # Usage tracking
    send_count: int = Field(default=0)
    last_sent_at: datetime | None = None

    # Relationships
    tenant: "Tenant" = Relationship()


class EmailTemplateCreate(SQLModel):
    """Schema for creating an email template."""

    name: str
    description: str | None = None
    subject: str
    body_html: str
    body_text: str | None = None
    design_json: dict | None = None
    default_form_id: UUID | None = None
    form_link_single_use: bool = True
    form_link_expires_days: int | None = 7
    attachments: list[dict] | None = None
    is_active: bool = True


class EmailTemplateRead(EmailTemplateBase):
    """Schema for reading an email template."""

    id: UUID
    tenant_id: UUID
    body_html: str
    body_text: str | None
    design_json: dict | None
    default_form_id: UUID | None
    form_link_single_use: bool
    form_link_expires_days: int | None
    attachments: list[dict]
    send_count: int
    last_sent_at: datetime | None
    created_at: datetime
    updated_at: datetime


class EmailTemplateUpdate(SQLModel):
    """Schema for updating an email template."""

    name: str | None = None
    description: str | None = None
    subject: str | None = None
    body_html: str | None = None
    body_text: str | None = None
    design_json: dict | None = None
    default_form_id: UUID | None = None
    form_link_single_use: bool | None = None
    form_link_expires_days: int | None = None
    attachments: list[dict] | None = None
    is_active: bool | None = None


# ============================================================================
# Tenant Email Configuration - per-tenant email provider settings
# ============================================================================


class TenantEmailConfig(BaseModel, table=True):
    """Tenant email provider configuration.

    Each tenant can configure their own email sending provider.
    Supports SMTP, AWS SES, Microsoft Graph, and SendGrid.
    """

    __tablename__ = "tenant_email_config"

    tenant_id: UUID = Field(foreign_key="tenant.id", unique=True, index=True)

    # Provider selection
    provider: str = Field(default="smtp")  # smtp, ses, graph, sendgrid
    is_active: bool = Field(default=True)

    # Common settings
    from_email: str  # Default sender email
    from_name: str | None = None  # Default sender name
    reply_to_email: str | None = None

    # Provider-specific configuration (encrypted sensitive fields)
    config: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    # Structure by provider:
    #
    # SMTP:
    # {
    #   "host": "smtp.example.com",
    #   "port": 587,
    #   "username": "user",
    #   "password_encrypted": "...",
    #   "use_tls": true,
    #   "use_ssl": false
    # }
    #
    # AWS SES:
    # {
    #   "region": "us-east-1",
    #   "access_key_id": "...",
    #   "secret_access_key_encrypted": "...",
    #   "configuration_set": "optional-config-set"
    # }
    #
    # Microsoft Graph:
    # {
    #   "client_id": "...",
    #   "client_secret_encrypted": "...",
    #   "tenant_id": "...",
    #   "user_id": "shared-mailbox@company.com"  # mailbox to send from
    # }
    #
    # SendGrid:
    # {
    #   "api_key_encrypted": "..."
    # }

    # Rate limiting
    max_sends_per_hour: int = Field(default=100)
    sends_this_hour: int = Field(default=0)
    hour_window_start: datetime | None = None

    # Tracking
    last_send_at: datetime | None = None
    last_error: str | None = None

    # Relationships
    tenant: "Tenant" = Relationship()


class TenantEmailConfigCreate(SQLModel):
    """Schema for creating tenant email config."""

    provider: EmailProvider
    from_email: str
    from_name: str | None = None
    reply_to_email: str | None = None
    config: dict
    max_sends_per_hour: int = 100
    is_active: bool = True


class TenantEmailConfigRead(SQLModel):
    """Schema for reading tenant email config (sensitive fields hidden)."""

    id: UUID
    tenant_id: UUID
    provider: str
    from_email: str
    from_name: str | None
    reply_to_email: str | None
    is_active: bool
    max_sends_per_hour: int
    last_send_at: datetime | None
    last_error: str | None
    # Note: config is NOT included - contains sensitive data


class TenantEmailConfigUpdate(SQLModel):
    """Schema for updating tenant email config."""

    provider: EmailProvider | None = None
    from_email: str | None = None
    from_name: str | None = None
    reply_to_email: str | None = None
    config: dict | None = None
    max_sends_per_hour: int | None = None
    is_active: bool | None = None


# ============================================================================
# Sent Email Log - track all outbound emails
# ============================================================================


class SentEmail(BaseModel, table=True):
    """Log of sent emails for tracking and debugging."""

    __tablename__ = "sent_email"

    tenant_id: UUID = Field(foreign_key="tenant.id", index=True)
    template_id: UUID | None = Field(default=None, foreign_key="email_template.id", index=True)

    # Recipient
    to_email: str = Field(index=True)
    to_name: str | None = None
    contact_id: UUID | None = Field(default=None, foreign_key="contact.id", index=True)

    # Content (snapshot at send time)
    subject: str
    body_html: str = Field(sa_column=Column(Text))
    body_text: str | None = Field(default=None, sa_column=Column(Text))

    # Sending context
    triggered_by: str | None = None  # "workflow", "campaign", "manual", "form_auto_reply"
    workflow_id: UUID | None = Field(default=None, foreign_key="workflow.id")
    workflow_execution_id: UUID | None = Field(default=None, foreign_key="workflow_execution.id")
    message_id: UUID | None = Field(default=None, foreign_key="message.id")  # Original message (for auto-replies)
    form_submission_id: UUID | None = Field(default=None, foreign_key="form_submission.id")

    # Form link that was included (if any)
    form_link_id: UUID | None = Field(default=None, foreign_key="form_link.id")

    # Delivery status
    status: str = Field(default="pending", index=True)  # pending, sent, delivered, bounced, failed
    sent_at: datetime | None = None
    provider_message_id: str | None = None  # ID from email provider
    error_message: str | None = None

    # Engagement tracking (populated by webhooks)
    opened_at: datetime | None = None
    clicked_at: datetime | None = None
    bounced_at: datetime | None = None
    unsubscribed_at: datetime | None = None


class SentEmailRead(SQLModel):
    """Schema for reading sent email log."""

    id: UUID
    tenant_id: UUID
    template_id: UUID | None
    to_email: str
    to_name: str | None
    contact_id: UUID | None
    subject: str
    triggered_by: str | None
    status: str
    sent_at: datetime | None
    error_message: str | None
    opened_at: datetime | None
    clicked_at: datetime | None
    created_at: datetime


# ============================================================================
# Template Variables Reference - for UI documentation
# ============================================================================

TEMPLATE_VARIABLES = {
    "contact": {
        "name": "Contact's full name",
        "email": "Contact's email address",
        "first_name": "Contact's first name (parsed from name)",
        "phone": "Contact's phone number",
    },
    "form": {
        "name": "Form name",
        "description": "Form description",
    },
    "form_link": {
        "url": "Pre-identified form link URL (auto-generated)",
        "expires_at": "Link expiration date",
    },
    "message": {
        "subject": "Original message subject",
        "sender_name": "Original sender name",
        "sender_email": "Original sender email",
        "received_at": "When message was received",
    },
    "tenant": {
        "name": "Organization name",
    },
    "custom": {
        "_description": "Custom contact fields by field name",
    },
}


# ============================================================================
# Email Suppression - unsubscribes, bounces, complaints
# ============================================================================


SuppressionType = Literal["unsubscribe", "hard_bounce", "soft_bounce", "complaint", "manual"]


class EmailSuppression(TenantBaseModel, table=True):
    """Email suppression list for bounces and unsubscribes.

    Prevents sending to emails that have bounced, unsubscribed, or complained.
    """

    __tablename__ = "email_suppression"

    # The suppressed email address
    email: str = Field(index=True)

    # Link to contact if known
    contact_id: UUID | None = Field(default=None, foreign_key="contact.id", index=True)

    # Type of suppression
    suppression_type: str = Field(index=True)  # unsubscribe, hard_bounce, soft_bounce, complaint, manual

    # Scope: global (all campaigns) or campaign-specific
    is_global: bool = Field(default=True)
    campaign_id: UUID | None = Field(default=None, foreign_key="campaign.id", index=True)

    # Source tracking
    source_campaign_id: UUID | None = Field(default=None, foreign_key="campaign.id")
    source_sent_email_id: UUID | None = Field(default=None, foreign_key="sent_email.id")

    # When suppressed
    suppressed_at: datetime = Field(default_factory=datetime.utcnow)

    # Provider-specific info
    provider_info: dict | None = Field(default=None, sa_column=Column(JSONB))
    # For bounces: {"bounce_type": "hard", "bounce_reason": "mailbox_not_found"}
    # For complaints: {"complaint_type": "abuse", "feedback_id": "..."}

    # Manual removal tracking
    is_active: bool = Field(default=True, index=True)
    removed_at: datetime | None = Field(default=None)
    removed_by_id: UUID | None = Field(default=None, foreign_key="user.id")
    removal_reason: str | None = Field(default=None, sa_column=Column(Text))

    # Relationships
    tenant: "Tenant" = Relationship()


class EmailSuppressionCreate(SQLModel):
    """Schema for creating a suppression entry."""

    email: str
    suppression_type: str = "manual"
    is_global: bool = True
    campaign_id: UUID | None = None


class EmailSuppressionRead(SQLModel):
    """Schema for reading a suppression entry."""

    id: UUID
    tenant_id: UUID
    email: str
    contact_id: UUID | None
    suppression_type: str
    is_global: bool
    campaign_id: UUID | None
    suppressed_at: datetime
    is_active: bool
    created_at: datetime
