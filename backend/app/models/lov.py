"""List of Values (LOV) model for tenant-configurable dropdown options."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.models.base import TenantBaseModel

if TYPE_CHECKING:
    from app.models.tenant import Tenant


# List type constants
LIST_TYPES = [
    "prefix",
    "pronoun",
    "language",
    "gender",
    "marital_status",
    "education_level",
    "income_bracket",
    "homeowner_status",
    "voter_status",
    "communication_pref",
    "inactive_reason",
]


class ListOfValues(TenantBaseModel, table=True):
    """Per-tenant list of values for dropdowns."""

    __tablename__ = "list_of_values"
    __table_args__ = (
        UniqueConstraint("tenant_id", "list_type", "value", name="uq_lov_tenant_type_value"),
    )

    list_type: str = Field(index=True)  # "prefix", "pronoun", "language", etc.
    value: str = Field(index=True)       # Stored value (e.g., "mr", "he_him")
    label: str                           # Display label (e.g., "Mr.", "he/him")
    sort_order: int = Field(default=0)
    is_active: bool = Field(default=True)

    # Relationships
    tenant: "Tenant" = Relationship(back_populates="list_of_values")


# Pydantic schemas for API
class LOVCreate(SQLModel):
    """Schema for creating a list of values entry."""

    value: str
    label: str
    sort_order: int = 0
    is_active: bool = True


class LOVUpdate(SQLModel):
    """Schema for updating a list of values entry."""

    value: str | None = None
    label: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class LOVRead(SQLModel):
    """Schema for reading a list of values entry."""

    id: UUID
    list_type: str
    value: str
    label: str
    sort_order: int
    is_active: bool


# Default seed data for new tenants
DEFAULT_LOV_DATA = {
    "prefix": [
        {"value": "mr", "label": "Mr."},
        {"value": "mrs", "label": "Mrs."},
        {"value": "ms", "label": "Ms."},
        {"value": "miss", "label": "Miss"},
        {"value": "dr", "label": "Dr."},
        {"value": "prof", "label": "Prof."},
        {"value": "rev", "label": "Rev."},
        {"value": "hon", "label": "Hon."},
    ],
    "pronoun": [
        {"value": "he_him", "label": "he/him"},
        {"value": "she_her", "label": "she/her"},
        {"value": "they_them", "label": "they/them"},
        {"value": "ze_zir", "label": "ze/zir"},
        {"value": "xe_xem", "label": "xe/xem"},
        {"value": "prefer_not_to_say", "label": "Prefer not to say"},
    ],
    "language": [
        {"value": "en", "label": "English"},
        {"value": "es", "label": "Spanish"},
        {"value": "zh", "label": "Chinese"},
        {"value": "vi", "label": "Vietnamese"},
        {"value": "ko", "label": "Korean"},
        {"value": "tl", "label": "Tagalog"},
        {"value": "ar", "label": "Arabic"},
        {"value": "fr", "label": "French"},
        {"value": "de", "label": "German"},
        {"value": "ru", "label": "Russian"},
        {"value": "pt", "label": "Portuguese"},
        {"value": "ja", "label": "Japanese"},
        {"value": "hi", "label": "Hindi"},
    ],
    "gender": [
        {"value": "male", "label": "Male"},
        {"value": "female", "label": "Female"},
        {"value": "non_binary", "label": "Non-binary"},
        {"value": "other", "label": "Other"},
        {"value": "prefer_not_to_say", "label": "Prefer not to say"},
    ],
    "marital_status": [
        {"value": "single", "label": "Single"},
        {"value": "married", "label": "Married"},
        {"value": "divorced", "label": "Divorced"},
        {"value": "widowed", "label": "Widowed"},
        {"value": "domestic_partnership", "label": "Domestic Partnership"},
    ],
    "education_level": [
        {"value": "high_school", "label": "High School"},
        {"value": "some_college", "label": "Some College"},
        {"value": "associates", "label": "Associate's Degree"},
        {"value": "bachelors", "label": "Bachelor's Degree"},
        {"value": "masters", "label": "Master's Degree"},
        {"value": "doctorate", "label": "Doctorate"},
    ],
    "income_bracket": [
        {"value": "under_25k", "label": "Under $25,000"},
        {"value": "25k_50k", "label": "$25,000 - $50,000"},
        {"value": "50k_75k", "label": "$50,000 - $75,000"},
        {"value": "75k_100k", "label": "$75,000 - $100,000"},
        {"value": "100k_150k", "label": "$100,000 - $150,000"},
        {"value": "over_150k", "label": "Over $150,000"},
    ],
    "homeowner_status": [
        {"value": "owner", "label": "Owner"},
        {"value": "renter", "label": "Renter"},
        {"value": "unknown", "label": "Unknown"},
    ],
    "voter_status": [
        {"value": "active", "label": "Active"},
        {"value": "inactive", "label": "Inactive"},
        {"value": "unregistered", "label": "Unregistered"},
    ],
    "communication_pref": [
        {"value": "email", "label": "Email"},
        {"value": "phone", "label": "Phone"},
        {"value": "mail", "label": "Mail"},
        {"value": "sms", "label": "SMS"},
    ],
    "inactive_reason": [
        {"value": "moved", "label": "Moved Away"},
        {"value": "deceased", "label": "Deceased"},
        {"value": "opt_out", "label": "Opted Out"},
        {"value": "invalid_contact", "label": "Invalid Contact Info"},
        {"value": "other", "label": "Other"},
    ],
}


def create_default_lov_entries(tenant_id: UUID) -> list[ListOfValues]:
    """Create default LOV entries for a new tenant."""
    entries = []
    for list_type, items in DEFAULT_LOV_DATA.items():
        for sort_order, item in enumerate(items):
            entries.append(
                ListOfValues(
                    tenant_id=tenant_id,
                    list_type=list_type,
                    value=item["value"],
                    label=item["label"],
                    sort_order=sort_order,
                    is_active=True,
                )
            )
    return entries
