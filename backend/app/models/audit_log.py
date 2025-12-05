"""Audit log model for tracking system activity."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.base import TenantBaseModel

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.user import User


# Action type constants
AUDIT_ACTIONS = [
    "created",
    "updated",
    "deleted",
    "archived",
    "restored",
    "merged",
    "imported",
    "exported",
    "assigned",
    "unassigned",
    "tagged",
    "untagged",
    "status_changed",
    "login",
    "logout",
    "api_key_created",
    "api_key_revoked",
    "permission_changed",
    "email_sent",
    "form_submitted",
    "workflow_triggered",
]

# Entity type constants
AUDIT_ENTITY_TYPES = [
    "contact",
    "message",
    "category",
    "campaign",
    "workflow",
    "form",
    "form_submission",
    "email_template",
    "user",
    "role",
    "api_key",
    "tenant",
    "job",
    "vote_history",
]


class AuditLog(TenantBaseModel, table=True):
    """Audit log for tracking all system activity."""

    __tablename__ = "audit_log"

    # What changed
    entity_type: str = Field(index=True)  # "contact", "message", "campaign", etc.
    entity_id: UUID | None = Field(default=None, index=True)  # ID of the affected record
    entity_name: str | None = Field(default=None)  # Human-readable name for display

    # What happened
    action: str = Field(index=True)  # "created", "updated", "deleted", etc.
    description: str = Field(sa_column=Column(Text))  # Human-readable description

    # Who did it
    user_id: UUID | None = Field(default=None, foreign_key="user.id", index=True)
    user_email: str | None = Field(default=None)  # Denormalized for display
    user_name: str | None = Field(default=None)  # Denormalized for display

    # Additional context
    ip_address: str | None = Field(default=None)
    user_agent: str | None = Field(default=None)

    # Change details (for updates)
    changes: dict | None = Field(default=None, sa_column=Column(JSONB))
    # Structure: {"field_name": {"old": "old_value", "new": "new_value"}}

    # Additional context
    extra_data: dict | None = Field(default=None, sa_column=Column(JSONB))
    # Can include: request_id, source (api/ui/webhook), related_entity_ids, etc.

    # Relationships
    tenant: "Tenant" = Relationship(back_populates="audit_logs")
    user: Optional["User"] = Relationship(back_populates="audit_logs")


# Pydantic schemas for API
class AuditLogCreate(SQLModel):
    """Schema for creating an audit log entry (internal use)."""

    entity_type: str
    entity_id: UUID | None = None
    entity_name: str | None = None
    action: str
    description: str
    user_id: UUID | None = None
    user_email: str | None = None
    user_name: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    changes: dict | None = None
    extra_data: dict | None = None


class AuditLogRead(SQLModel):
    """Schema for reading an audit log entry."""

    id: UUID
    tenant_id: UUID
    entity_type: str
    entity_id: UUID | None
    entity_name: str | None
    action: str
    description: str
    user_id: UUID | None
    user_email: str | None
    user_name: str | None
    ip_address: str | None
    changes: dict | None
    extra_data: dict | None
    created_at: datetime


class AuditLogListResponse(SQLModel):
    """Paginated audit log response."""

    items: list[AuditLogRead]
    total: int
    page: int
    page_size: int
    pages: int
