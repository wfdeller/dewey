"""Form builder models for surveys and data collection."""

from datetime import datetime
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.base import BaseModel, TenantBaseModel

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.contact import Contact
    from app.models.message import Message


FormStatus = Literal["draft", "published", "archived"]
FieldType = Literal[
    "text",
    "textarea",
    "email",
    "phone",
    "select",
    "multi_select",
    "radio",
    "checkbox",
    "date",
    "number",
    "rating",
    "nps",
    "file_upload",
    "hidden",
]
SubmissionStatus = Literal["pending", "processed", "spam"]


class FormBase(SQLModel):
    """Form base schema."""

    name: str = Field(index=True)
    description: str | None = Field(default=None, sa_column=Column(Text))
    slug: str = Field(index=True)  # URL-safe identifier
    status: str = Field(default="draft")  # draft, published, archived


class Form(FormBase, TenantBaseModel, table=True):
    """Form database model."""

    __tablename__ = "form"

    # Form settings
    settings: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    # Structure: {
    #   "submit_button_text": "Submit",
    #   "success_message": "Thank you!",
    #   "redirect_url": null,
    #   "notification_emails": [],
    #   "auto_response_enabled": false,
    #   "auto_response_template": null,
    #   "captcha_enabled": true,
    #   "require_authentication": false,
    #   "expires_at": null
    # }

    # Form styling
    styling: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    # Structure: {"primary_color": "#1890ff", "font_family": "...", "custom_css": ""}

    # Relationships
    tenant: "Tenant" = Relationship(back_populates="forms")
    fields: list["FormField"] = Relationship(back_populates="form")
    submissions: list["FormSubmission"] = Relationship(back_populates="form")


class FormField(BaseModel, table=True):
    """Form field definition."""

    __tablename__ = "form_field"

    form_id: UUID = Field(foreign_key="form.id", index=True)

    # Field configuration
    field_type: str  # text, textarea, email, phone, select, multi_select, radio, checkbox, date, number, rating, nps, file_upload, hidden
    label: str
    placeholder: str | None = None
    help_text: str | None = None
    is_required: bool = Field(default=False)
    sort_order: int = Field(default=0)

    # Validation rules
    validation: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    # Structure: {"min": 0, "max": 100, "pattern": "regex", "min_length": 1}

    # Options for select/radio/checkbox fields
    options: list[dict] = Field(default_factory=list, sa_column=Column(JSONB))
    # Structure: [{"value": "option1", "label": "Option 1"}]

    # Conditional logic
    conditional_logic: dict | None = Field(default=None, sa_column=Column(JSONB))
    # Structure: {"show_if": {"field_id": "uuid", "operator": "equals", "value": "..."}}

    # Contact field mapping
    maps_to_contact_field: str | None = None  # email, name, phone, address
    maps_to_custom_field_id: UUID | None = Field(default=None, foreign_key="custom_field_definition.id")

    # Field-specific settings
    settings: dict = Field(default_factory=dict, sa_column=Column(JSONB))

    # Relationships
    form: Form = Relationship(back_populates="fields")


class FormSubmission(BaseModel, table=True):
    """Form submission record."""

    __tablename__ = "form_submission"

    form_id: UUID = Field(foreign_key="form.id", index=True)
    contact_id: UUID | None = Field(default=None, foreign_key="contact.id", index=True)
    message_id: UUID | None = Field(default=None, foreign_key="message.id", unique=True)

    # Submission data
    submitted_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    field_values: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    # Structure: {"field_id": "value", ...}

    # Metadata
    ip_address: str | None = None
    user_agent: str | None = Field(default=None, sa_column=Column(Text))
    referrer_url: str | None = None
    utm_params: dict = Field(default_factory=dict, sa_column=Column(JSONB))

    # Processing
    status: str = Field(default="pending")  # pending, processed, spam
    spam_score: float | None = None

    # Relationships
    form: Form = Relationship(back_populates="submissions")
    contact: "Contact" = Relationship()
    message: "Message" = Relationship()


class FormCreate(FormBase):
    """Schema for creating a form."""

    settings: dict | None = None
    styling: dict | None = None


class FormRead(FormBase):
    """Schema for reading a form."""

    id: UUID
    tenant_id: UUID
    settings: dict | None = None
    styling: dict | None = None


class FormFieldCreate(SQLModel):
    """Schema for creating a form field."""

    field_type: FieldType
    label: str
    placeholder: str | None = None
    help_text: str | None = None
    is_required: bool = False
    sort_order: int = 0
    validation: dict | None = None
    options: list[dict] | None = None
    conditional_logic: dict | None = None
    maps_to_contact_field: str | None = None
    maps_to_custom_field_id: UUID | None = None
    settings: dict | None = None


class FormFieldRead(SQLModel):
    """Schema for reading a form field."""

    id: UUID
    form_id: UUID
    field_type: FieldType
    label: str
    placeholder: str | None = None
    help_text: str | None = None
    is_required: bool = False
    sort_order: int = 0
    validation: dict | None = None
    options: list[dict] | None = None
    conditional_logic: dict | None = None


class FormSubmissionCreate(SQLModel):
    """Schema for submitting a form."""

    field_values: dict
    ip_address: str | None = None
    user_agent: str | None = None
    referrer_url: str | None = None
    utm_params: dict | None = None


class FormSubmissionRead(SQLModel):
    """Schema for reading a form submission."""

    id: UUID
    form_id: UUID
    contact_id: UUID | None
    message_id: UUID | None
    submitted_at: datetime
    field_values: dict
    status: SubmissionStatus


# ============================================================================
# Form Links - Pre-identified user tokens for form submissions
# ============================================================================


class FormLink(BaseModel, table=True):
    """Trackable form link for pre-identified users.

    Allows generating unique URLs with tokens that pre-identify a contact,
    so form submissions are automatically linked without requiring email entry.
    """

    __tablename__ = "form_link"

    form_id: UUID = Field(foreign_key="form.id", index=True)
    contact_id: UUID = Field(foreign_key="contact.id", index=True)

    # URL-safe random token (unique identifier for the link)
    token: str = Field(unique=True, index=True)

    # Configuration
    is_single_use: bool = Field(default=False)  # Invalidate after first submission
    expires_at: datetime | None = None

    # Tracking
    used_at: datetime | None = None  # First use timestamp
    use_count: int = Field(default=0)  # Total submissions via this link

    # Relationships
    form: Form = Relationship()
    contact: "Contact" = Relationship()


class FormLinkCreate(SQLModel):
    """Schema for creating a form link."""

    contact_id: UUID
    is_single_use: bool = False
    expires_at: datetime | None = None


class FormLinkRead(SQLModel):
    """Schema for reading a form link."""

    id: UUID
    form_id: UUID
    contact_id: UUID
    token: str
    is_single_use: bool
    expires_at: datetime | None
    used_at: datetime | None
    use_count: int
    created_at: datetime


class FormLinkBulkCreate(SQLModel):
    """Schema for bulk creating form links."""

    contact_ids: list[UUID]
    is_single_use: bool = False
    expires_at: datetime | None = None


class FormLinkBulkResponse(SQLModel):
    """Response schema for bulk link creation."""

    links: list[FormLinkRead]
    created_count: int
