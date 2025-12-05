"""Job model for tracking background processing tasks."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.base import TenantBaseModel

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.user import User
    from app.models.vote_history import VoteHistory


# Job type constants
JOB_TYPES = [
    "voter_import",
    "contact_export",
]

# Job status constants
JOB_STATUSES = [
    "pending",
    "analyzing",
    "mapping",
    "processing",
    "completed",
    "failed",
    "cancelled",
]


class Job(TenantBaseModel, table=True):
    """Generic job tracking for background processing."""

    __tablename__ = "job"

    job_type: str = Field(index=True)  # "voter_import", "contact_export", etc.
    status: str = Field(default="pending", index=True)

    # File info (for import jobs)
    original_filename: str | None = Field(default=None)
    file_path: str | None = Field(default=None)
    file_size_bytes: int | None = Field(default=None)
    total_rows: int | None = Field(default=None)

    # AI mappings (for import jobs) - stored as JSONB
    detected_headers: list[str] | None = Field(default=None, sa_column=Column(JSONB))
    suggested_mappings: dict | None = Field(default=None, sa_column=Column(JSONB))
    # Structure: {header: {field: "email", confidence: 0.95}}
    confirmed_mappings: dict | None = Field(default=None, sa_column=Column(JSONB))
    # Structure: {header: "email"} - user confirmed

    # Matching strategy (for import jobs)
    matching_strategy: str | None = Field(default=None)  # "email_first", "voter_id_first", etc.
    suggested_matching_strategy: str | None = Field(default=None)
    matching_strategy_reason: str | None = Field(default=None, sa_column=Column(Text))  # AI explanation

    # Progress tracking
    rows_processed: int = Field(default=0)
    rows_created: int = Field(default=0)
    rows_updated: int = Field(default=0)
    rows_skipped: int = Field(default=0)
    rows_errored: int = Field(default=0)

    # Error tracking
    error_message: str | None = Field(default=None, sa_column=Column(Text))
    error_details: list[dict] | None = Field(default=None, sa_column=Column(JSONB))
    # Structure: [{row: 5, field: "email", error: "Invalid format"}]

    # Timing
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)

    # Owner
    created_by_id: UUID = Field(foreign_key="user.id", index=True)

    # Relationships
    tenant: "Tenant" = Relationship(back_populates="jobs")
    created_by: "User" = Relationship(back_populates="jobs")
    vote_histories: list["VoteHistory"] = Relationship(back_populates="job")


# Pydantic schemas for API
class JobCreate(SQLModel):
    """Schema for creating a job (typically internal use)."""

    job_type: str
    original_filename: str | None = None
    file_path: str | None = None
    file_size_bytes: int | None = None


class JobRead(SQLModel):
    """Schema for reading a job."""

    id: UUID
    tenant_id: UUID
    job_type: str
    status: str

    # File info
    original_filename: str | None
    file_size_bytes: int | None
    total_rows: int | None

    # Mappings
    detected_headers: list[str] | None
    suggested_mappings: dict | None
    confirmed_mappings: dict | None

    # Matching
    matching_strategy: str | None
    suggested_matching_strategy: str | None
    matching_strategy_reason: str | None

    # Progress
    rows_processed: int
    rows_created: int
    rows_updated: int
    rows_skipped: int
    rows_errored: int

    # Errors
    error_message: str | None
    error_details: list[dict] | None

    # Timing
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    # Owner
    created_by_id: UUID


class JobProgress(SQLModel):
    """Real-time progress update schema."""

    status: str
    rows_processed: int
    rows_created: int
    rows_updated: int
    rows_skipped: int
    rows_errored: int
    total_rows: int | None
    percent_complete: float | None


class JobConfirmMappings(SQLModel):
    """Schema for confirming field mappings and matching strategy."""

    confirmed_mappings: dict  # {header: field_name}
    matching_strategy: str  # "email_first", "voter_id_first", etc.
