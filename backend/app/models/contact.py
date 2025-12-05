"""Contact model for sender/constituent tracking with custom fields."""

import re
from datetime import datetime, date
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from pydantic import field_validator
from sqlalchemy import Column, UniqueConstraint, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlmodel import Field, Relationship, SQLModel, String

from app.models.base import BaseModel, TenantBaseModel


# =============================================================================
# Data Cleaning Utilities
# =============================================================================

def clean_name_field(value: str | None) -> str | None:
    """Clean and normalize a name field to title case."""
    if not value or not isinstance(value, str):
        return value
    cleaned = value.strip()
    if not cleaned:
        return None
    return cleaned.title()


def clean_phone_field(value: str | None) -> str | None:
    """Clean and format phone number to (555) 555-5555 format."""
    if not value or not isinstance(value, str):
        return value
    cleaned = value.strip()
    if not cleaned:
        return None

    # Extract only digits
    digits = re.sub(r'\D', '', cleaned)

    # Format based on digit count
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits[0] == '1':
        return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"

    # Return original if can't parse
    return cleaned


def clean_email_field(value: str | None) -> str | None:
    """Clean email to lowercase and strip whitespace."""
    if not value or not isinstance(value, str):
        return value
    cleaned = value.strip().lower()
    return cleaned if cleaned else None


def clean_prefix_field(value: str | None) -> str | None:
    """Normalize prefix to standard format."""
    if not value or not isinstance(value, str):
        return value
    cleaned = value.strip()
    if not cleaned:
        return None

    # Map common variations to canonical form
    prefix_map = {
        'mr': 'Mr.', 'mr.': 'Mr.',
        'mrs': 'Mrs.', 'mrs.': 'Mrs.',
        'ms': 'Ms.', 'ms.': 'Ms.',
        'miss': 'Miss', 'miss.': 'Miss',
        'dr': 'Dr.', 'dr.': 'Dr.',
        'prof': 'Prof.', 'prof.': 'Prof.',
        'rev': 'Rev.', 'rev.': 'Rev.',
        'hon': 'Hon.', 'hon.': 'Hon.',
    }
    normalized = cleaned.lower()
    return prefix_map.get(normalized, cleaned.title())

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.message import Message


FieldType = Literal["text", "select", "multi_select", "number", "date", "boolean"]


class ContactBase(SQLModel):
    """Contact base schema."""

    email: str = Field(index=True)
    name: str | None = None
    phone: str | None = None

    # Status - whether contact is still relevant for outreach
    is_active: bool = Field(default=True)  # False if moved away, deceased, opt-out, etc.
    inactive_reason: str | None = Field(default=None)  # "moved", "deceased", "opt_out", "invalid_contact", "other"

    # Demographics (can be extracted from messages or entered manually)
    date_of_birth: date | None = Field(default=None)
    age_estimate: int | None = Field(default=None)  # Estimated age if DOB unknown
    age_estimate_source: str | None = Field(default=None)  # "manual", "inferred", "public_records"
    gender: str | None = Field(default=None)  # "male", "female", "non_binary", "other", "unknown"
    pronouns: str | None = Field(default=None)  # "he_him", "she_her", "they_them", etc.

    # Extended demographics for targeting
    prefix: str | None = Field(default=None)  # Mr., Mrs., Dr., etc.
    first_name: str | None = Field(default=None)
    middle_name: str | None = Field(default=None)
    last_name: str | None = Field(default=None)
    suffix: str | None = Field(default=None)  # Jr., Sr., III, etc.
    preferred_name: str | None = Field(default=None)  # Nickname or preferred name

    # Professional/occupational
    occupation: str | None = Field(default=None)
    employer: str | None = Field(default=None)
    job_title: str | None = Field(default=None)
    industry: str | None = Field(default=None)

    # Voter/political info (for constituent management)
    voter_status: str | None = Field(default=None)  # "active", "inactive", "unregistered"
    party_affiliation: str | None = Field(default=None)  # "democrat", "republican", "independent", etc.
    voter_registration_date: date | None = Field(default=None)

    # Socioeconomic indicators (inferred or from public data)
    income_bracket: str | None = Field(default=None)  # "under_25k", "25k_50k", "50k_75k", "75k_100k", "100k_150k", "over_150k"
    education_level: str | None = Field(default=None)  # "high_school", "some_college", "bachelors", "masters", "doctorate"
    homeowner_status: str | None = Field(default=None)  # "owner", "renter", "unknown"

    # Household info
    household_size: int | None = Field(default=None)
    has_children: bool | None = Field(default=None)
    marital_status: str | None = Field(default=None)  # "single", "married", "divorced", "widowed"

    # Language/communication preferences
    preferred_language: str | None = Field(default=None)  # ISO 639-1 code, e.g., "en", "es"
    communication_preference: str | None = Field(default=None)  # "email", "phone", "mail", "sms"

    # Additional contact methods
    secondary_email: str | None = Field(default=None)
    mobile_phone: str | None = Field(default=None)
    work_phone: str | None = Field(default=None)


class Contact(ContactBase, TenantBaseModel, table=True):
    """Contact database model for sender/constituent tracking."""

    __tablename__ = "contact"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_contact_tenant_email"),)

    # Address (stored as JSON for flexibility)
    address: dict | None = Field(default=None, sa_column=Column(JSONB))
    # Structure: {
    #   street, street2, city, state, zip, country,
    #   county, congressional_district, state_legislative_district,
    #   precinct, latitude, longitude
    # }

    # Geographic targeting (denormalized from address for efficient queries)
    state: str | None = Field(default=None, index=True)  # 2-letter code
    zip_code: str | None = Field(default=None, index=True)
    county: str | None = Field(default=None, index=True)
    congressional_district: str | None = Field(default=None, index=True)  # e.g., "CA-12"
    state_legislative_district: str | None = Field(default=None, index=True)  # State senate/assembly

    # Geolocation (for mapping and radius searches)
    latitude: float | None = Field(default=None)
    longitude: float | None = Field(default=None)

    # Aggregated stats (denormalized for performance)
    first_contact_at: datetime | None = Field(default=None)
    last_contact_at: datetime | None = Field(default=None)
    message_count: int = Field(default=0)

    # Dominant tones across all messages from this contact
    # Computed from the most frequent tones in message analyses
    dominant_tones: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String)))

    # Deprecated - kept for migration period
    avg_sentiment: float | None = Field(default=None)

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

    # Data cleaning validators
    @field_validator('first_name', 'last_name', 'middle_name', 'preferred_name', mode='before')
    @classmethod
    def clean_names(cls, v: str | None) -> str | None:
        return clean_name_field(v)

    @field_validator('phone', 'mobile_phone', 'work_phone', mode='before')
    @classmethod
    def clean_phones(cls, v: str | None) -> str | None:
        return clean_phone_field(v)

    @field_validator('email', 'secondary_email', mode='before')
    @classmethod
    def clean_emails(cls, v: str | None) -> str | None:
        return clean_email_field(v)

    @field_validator('prefix', mode='before')
    @classmethod
    def clean_prefix(cls, v: str | None) -> str | None:
        return clean_prefix_field(v)


class ContactRead(ContactBase):
    """Schema for reading a contact."""

    id: UUID
    tenant_id: UUID
    address: dict | None

    # Geographic targeting fields
    state: str | None
    zip_code: str | None
    county: str | None
    congressional_district: str | None
    state_legislative_district: str | None
    latitude: float | None
    longitude: float | None

    # Stats
    first_contact_at: datetime | None
    last_contact_at: datetime | None
    message_count: int
    dominant_tones: list[str]
    avg_sentiment: float | None  # Deprecated
    tags: list[str]
    notes: str | None
    created_at: datetime


class ContactUpdate(SQLModel):
    """Schema for updating a contact."""

    # Basic info
    name: str | None = None
    email: str | None = None
    phone: str | None = None

    # Status
    is_active: bool | None = None
    inactive_reason: str | None = None

    # Demographics
    date_of_birth: date | None = None
    age_estimate: int | None = None
    age_estimate_source: str | None = None
    gender: str | None = None
    pronouns: str | None = None

    # Name components
    prefix: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    last_name: str | None = None
    suffix: str | None = None
    preferred_name: str | None = None

    # Professional
    occupation: str | None = None
    employer: str | None = None
    job_title: str | None = None
    industry: str | None = None

    # Voter/political
    voter_status: str | None = None
    party_affiliation: str | None = None
    voter_registration_date: date | None = None

    # Socioeconomic
    income_bracket: str | None = None
    education_level: str | None = None
    homeowner_status: str | None = None

    # Household
    household_size: int | None = None
    has_children: bool | None = None
    marital_status: str | None = None

    # Communication
    preferred_language: str | None = None
    communication_preference: str | None = None
    secondary_email: str | None = None
    mobile_phone: str | None = None
    work_phone: str | None = None

    # Address and location
    address: dict | None = None
    state: str | None = None
    zip_code: str | None = None
    county: str | None = None
    congressional_district: str | None = None
    state_legislative_district: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    # Other
    tags: list[str] | None = None
    notes: str | None = None
    custom_fields: dict[str, str | float | date | bool | list[str]] | None = None

    # Data cleaning validators
    @field_validator('first_name', 'last_name', 'middle_name', 'preferred_name', mode='before')
    @classmethod
    def clean_names(cls, v: str | None) -> str | None:
        return clean_name_field(v)

    @field_validator('phone', 'mobile_phone', 'work_phone', mode='before')
    @classmethod
    def clean_phones(cls, v: str | None) -> str | None:
        return clean_phone_field(v)

    @field_validator('email', 'secondary_email', mode='before')
    @classmethod
    def clean_emails(cls, v: str | None) -> str | None:
        return clean_email_field(v)

    @field_validator('prefix', mode='before')
    @classmethod
    def clean_prefix(cls, v: str | None) -> str | None:
        return clean_prefix_field(v)


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
