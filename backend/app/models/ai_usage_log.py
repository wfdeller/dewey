"""AI usage log model for tracking token usage and costs."""

from typing import TYPE_CHECKING, Literal
from uuid import UUID

from sqlmodel import Field, Relationship, SQLModel

from app.models.base import TenantBaseModel

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.user import User


OperationType = Literal[
    "message_analysis",
    "categorization",
    "field_mapping",
    "matching_strategy",
    "contact_engagement",
    "segment_analysis",
    "schema_recommendation",
    "other",
]

AILogStatus = Literal["success", "error", "timeout"]


class AIUsageLogBase(SQLModel):
    """Base schema for AI usage logs."""

    operation_type: str = Field(index=True)  # "message_analysis", "voter_import", etc.
    operation_id: str | None = None  # e.g., message_id, job_id


class AIUsageLog(AIUsageLogBase, TenantBaseModel, table=True):
    """Log every AI API call for analytics and billing."""

    __tablename__ = "ai_usage_log"

    # Provider details
    ai_provider: str = Field(index=True)  # claude, openai, azure_openai, ollama
    ai_model: str
    prompt_template_id: UUID | None = Field(default=None, foreign_key="prompt_template.id")

    # Token metrics
    input_tokens: int = Field(default=0)
    output_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)

    # Cost tracking (optional, for billing)
    estimated_cost_usd: float | None = Field(default=None)

    # Performance
    processing_time_ms: int = Field(default=0)

    # Status
    status: str = Field(default="success")  # success, error, timeout
    error_message: str | None = Field(default=None)

    # User who initiated (if applicable)
    user_id: UUID | None = Field(default=None, foreign_key="user.id")

    # Relationships
    tenant: "Tenant" = Relationship()
    user: "User" = Relationship()


class AIUsageLogRead(AIUsageLogBase):
    """Schema for reading AI usage log entries."""

    id: UUID
    tenant_id: UUID
    ai_provider: str
    ai_model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: float | None
    processing_time_ms: int
    status: str
    error_message: str | None
    user_id: UUID | None


class AIUsageStats(SQLModel):
    """Aggregated AI usage statistics."""

    total_tokens: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_calls: int = 0
    success_count: int = 0
    error_count: int = 0
    average_processing_time_ms: float = 0.0
    estimated_total_cost_usd: float = 0.0
    by_provider: dict[str, int] = {}
    by_operation: dict[str, int] = {}
    by_model: dict[str, int] = {}
