"""Vote history model for tracking voter participation."""

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.models.base import TenantBaseModel

if TYPE_CHECKING:
    from app.models.contact import Contact
    from app.models.job import Job
    from app.models.tenant import Tenant


class VoteHistory(TenantBaseModel, table=True):
    """Per-contact voting history records."""

    __tablename__ = "vote_history"
    __table_args__ = (
        UniqueConstraint(
            "contact_id", "election_date", "election_type",
            name="uq_vote_history_contact_election"
        ),
    )

    contact_id: UUID = Field(foreign_key="contact.id", index=True)
    election_name: str = Field(index=True)  # "2024 General Election"
    election_date: date = Field(index=True)
    election_type: str = Field(index=True)  # "general", "primary", "special", "municipal", "runoff"
    voted: bool | None = Field(default=None)  # True/False/Unknown
    voting_method: str | None = Field(default=None)  # "election_day", "early", "absentee", "mail"
    primary_party_voted: str | None = Field(default=None)  # Which party ballot pulled (for primaries)

    # Import tracking
    job_id: UUID | None = Field(default=None, foreign_key="job.id", index=True)
    source_file_name: str | None = Field(default=None)
    imported_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    tenant: "Tenant" = Relationship(back_populates="vote_histories")
    contact: "Contact" = Relationship(back_populates="vote_histories")
    job: Optional["Job"] = Relationship(back_populates="vote_histories")


# Pydantic schemas for API
class VoteHistoryCreate(SQLModel):
    """Schema for creating a vote history record."""

    contact_id: UUID
    election_name: str
    election_date: date
    election_type: str
    voted: bool | None = None
    voting_method: str | None = None
    primary_party_voted: str | None = None


class VoteHistoryRead(SQLModel):
    """Schema for reading a vote history record."""

    id: UUID
    contact_id: UUID
    election_name: str
    election_date: date
    election_type: str
    voted: bool | None
    voting_method: str | None
    primary_party_voted: str | None
    source_file_name: str | None
    imported_at: datetime
    created_at: datetime


class VoteHistorySummary(SQLModel):
    """Aggregated voting statistics for a contact."""

    total_elections: int
    elections_voted: int
    elections_missed: int
    elections_unknown: int
    vote_rate: float  # percentage
    general_elections_voted: int
    primary_elections_voted: int
    last_voted_date: date | None
    last_voted_election: str | None
    most_common_method: str | None
