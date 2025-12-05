"""Contact model for sender/constituent tracking with custom fields."""

from datetime import datetime, date
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from sqlalchemy import Column, UniqueConstraint, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlmodel import Field, Relationship, SQLModel, String

from app.models.base import BaseModel, TenantBaseModel

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.message import Message


FieldType = Literal["text", "select", "multi_select", "number", "date", "boolean"]


class ContactBase(SQLModel):
    """Contact base schema."""

    email: str = Field(index=True)
    name: str | None = None
    phone: str | None = None


class Contact(ContactBase, TenantBaseModel, table=True):
    """Contact database model for sender/constituent tracking."""

    __tablename__ = "contact"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_contact_tenant_email"),)

    # Address (stored as JSON for flexibility)
    address: dict | None = Field(default=None, sa_column=Column(JSONB))
    # Structure: {street, city, state, zip, country, district}

    # Aggregated stats (denormalized for performance)
    first_contact_at: datetime | None = Field(default=None)
    last_contact_at: datetime | None = Field(default=None)
    message_count: int = Field(default=0)
    avg_sentiment: float | None = Field(default=None)  # Rolling average

    # Tags for quick categorization
    tags: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String)))

    # Staff notes
    notes: str | None = Field(default=None, sa_column=Column(Text))

    # Relationships
    tenant: "Tenant" = Relationship(back_populates="contacts")
    messages: list["Message"] = Relationship(back_populates="contact")
    field_values: list["ContactFieldValue"] = Relationship(back_populates="contact")


class CustomFieldDefinition(TenantBaseModel, table=True):
    """Tenant-configurable custom field definitions."""

    __tablename__ = "custom_field_definition"
    __table_args__ = (
        UniqueConstraint("tenant_id", "field_key", name="uq_field_tenant_key"),
    )

    name: str = Field(index=True)  # Display name, e.g., "Party Affiliation"
    field_key: str  # Slug for API, e.g., "party_affiliation"
    field_type: str = Field(default="text")  # text, select, multi_select, number, date, boolean

    # Options for select/multi_select fields
    options: list[dict] = Field(default_factory=list, sa_column=Column(JSONB))
    # Structure: [{"value": "democrat", "label": "Democrat", "color": "#0000FF"}]

    # Field settings
    is_required: bool = Field(default=False)
    is_searchable: bool = Field(default=True, index=True)
    is_visible_in_list: bool = Field(default=True)
    sort_order: int = Field(default=0)

    # Relationships
    tenant: "Tenant" = Relationship(back_populates="custom_field_definitions")
    field_values: list["ContactFieldValue"] = Relationship(back_populates="field_definition")


class ContactFieldValue(BaseModel, table=True):
    """Custom field values for contacts (polymorphic value storage)."""

    __tablename__ = "contact_field_value"
    __table_args__ = (
        UniqueConstraint("contact_id", "field_definition_id", name="uq_contact_field"),
    )

    contact_id: UUID = Field(foreign_key="contact.id", index=True)
    field_definition_id: UUID = Field(foreign_key="custom_field_definition.id", index=True)

    # Polymorphic value storage (only one is used based on field_type)
    value_text: str | None = Field(default=None, sa_column=Column(Text))
    value_option: str | None = Field(default=None, index=True)  # For select
    value_options: list[str] | None = Field(default=None, sa_column=Column(ARRAY(String)))  # For multi_select
    value_number: float | None = Field(default=None)
    value_date: date | None = Field(default=None)
    value_boolean: bool | None = Field(default=None)

    # Relationships
    contact: Contact = Relationship(back_populates="field_values")
    field_definition: CustomFieldDefinition = Relationship(back_populates="field_values")

    def get_value(self) -> str | float | date | bool | list[str] | None:
        """Get the value based on the field type."""
        field_type = self.field_definition.field_type
        if field_type == "text":
            return self.value_text
        elif field_type == "select":
            return self.value_option
        elif field_type == "multi_select":
            return self.value_options
        elif field_type == "number":
            return self.value_number
        elif field_type == "date":
            return self.value_date
        elif field_type == "boolean":
            return self.value_boolean
        return None


class ContactCreate(ContactBase):
    """Schema for creating a contact."""

    address: dict | None = None
    tags: list[str] = []
    notes: str | None = None
    custom_fields: dict[str, str | float | date | bool | list[str]] | None = None


class ContactRead(ContactBase):
    """Schema for reading a contact."""

    id: UUID
    tenant_id: UUID
    address: dict | None
    first_contact_at: datetime | None
    last_contact_at: datetime | None
    message_count: int
    avg_sentiment: float | None
    tags: list[str]
    created_at: datetime


class ContactUpdate(SQLModel):
    """Schema for updating a contact."""

    name: str | None = None
    phone: str | None = None
    address: dict | None = None
    tags: list[str] | None = None
    notes: str | None = None
    custom_fields: dict[str, str | float | date | bool | list[str]] | None = None


class CustomFieldCreate(SQLModel):
    """Schema for creating a custom field definition."""

    name: str
    field_key: str
    field_type: FieldType = "text"
    options: list[dict] = []
    is_required: bool = False
    is_searchable: bool = True
    is_visible_in_list: bool = True
    sort_order: int = 0


class CustomFieldRead(SQLModel):
    """Schema for reading a custom field definition."""

    id: UUID
    tenant_id: UUID
    name: str
    field_key: str
    field_type: FieldType
    options: list[dict]
    is_required: bool
    is_searchable: bool
    is_visible_in_list: bool
    sort_order: int
