"""Base model classes with common fields and functionality."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class TimestampMixin(SQLModel):
    """Mixin for created_at and updated_at timestamps."""

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
    )


class SoftDeleteMixin(SQLModel):
    """Mixin for soft delete functionality."""

    deleted_at: datetime | None = Field(default=None, nullable=True)
    is_deleted: bool = Field(default=False, nullable=False)


class BaseModel(TimestampMixin):
    """Base model with UUID primary key and timestamps."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)


class TenantBaseModel(BaseModel):
    """Base model for tenant-scoped entities."""

    tenant_id: UUID = Field(foreign_key="tenant.id", index=True)
