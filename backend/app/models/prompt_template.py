"""Prompt template model for per-tenant customizable AI prompts."""

from typing import TYPE_CHECKING, Literal
from uuid import UUID

from sqlalchemy import Column, Text
from sqlmodel import Field, Relationship, SQLModel

from app.models.base import TenantBaseModel

if TYPE_CHECKING:
    from app.models.tenant import Tenant


PromptName = Literal[
    "message_analysis",
    "categorization",
    "field_mapping",
    "matching_strategy",
    "contact_engagement",
    "segment_analysis",
    "schema_recommendation",
]


class PromptTemplateBase(SQLModel):
    """Base schema for prompt templates."""

    name: str = Field(index=True)  # "message_analysis", "categorization", etc.
    description: str | None = None
    is_active: bool = Field(default=True)


class PromptTemplate(PromptTemplateBase, TenantBaseModel, table=True):
    """Per-tenant customizable prompt templates."""

    __tablename__ = "prompt_template"

    # The actual prompts (stored as Text for large content)
    system_prompt: str = Field(sa_column=Column(Text, nullable=False))
    user_prompt_template: str = Field(sa_column=Column(Text, nullable=False))

    # Version tracking for rollback
    version: int = Field(default=1)
    previous_version_id: UUID | None = Field(default=None, foreign_key="prompt_template.id")

    # Provider-specific settings
    temperature: float = Field(default=0.3)
    max_tokens: int = Field(default=2000)

    # Relationships
    tenant: "Tenant" = Relationship()


class PromptTemplateCreate(PromptTemplateBase):
    """Schema for creating a prompt template."""

    system_prompt: str
    user_prompt_template: str
    temperature: float = 0.3
    max_tokens: int = 2000


class PromptTemplateRead(PromptTemplateBase):
    """Schema for reading a prompt template."""

    id: UUID
    tenant_id: UUID
    system_prompt: str
    user_prompt_template: str
    version: int
    temperature: float
    max_tokens: int


class PromptTemplateUpdate(SQLModel):
    """Schema for updating a prompt template."""

    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    user_prompt_template: str | None = None
    is_active: bool | None = None
    temperature: float | None = None
    max_tokens: int | None = None
