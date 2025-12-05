"""Tenant (organization) model."""

from typing import TYPE_CHECKING, Literal
from uuid import UUID

from pydantic import model_validator
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.category import Category
    from app.models.message import Message
    from app.models.workflow import Workflow
    from app.models.contact import Contact, CustomFieldDefinition
    from app.models.form import Form
    from app.models.campaign import Campaign
    from app.models.api_key import APIKey
    from app.models.lov import ListOfValues
    from app.models.vote_history import VoteHistory
    from app.models.job import Job
    from app.models.audit_log import AuditLog


SubscriptionTier = Literal["free", "pro", "enterprise"]
AIProvider = Literal["claude", "openai", "azure_openai", "ollama"]
AIKeySource = Literal["platform", "tenant"]  # platform = Dewey's key, tenant = customer's key


class TenantBase(SQLModel):
    """Tenant base schema."""

    name: str = Field(index=True)
    slug: str = Field(unique=True, index=True, max_length=63)
    subscription_tier: str = Field(default="free")  # free, pro, enterprise


class Tenant(TenantBase, BaseModel, table=True):
    """Tenant (organization) database model."""

    __tablename__ = "tenant"

    # Marketplace integration
    marketplace_subscription_id: str | None = Field(default=None, index=True)
    marketplace_provider: str | None = Field(default=None)  # azure, aws

    # AI Provider Configuration
    # - ai_provider: which provider to use
    # - ai_key_source: "platform" (Dewey's shared key) or "tenant" (customer's own key)
    # - ai_provider_config: encrypted keys and provider-specific settings
    ai_provider: str = Field(default="claude")  # claude, openai, azure_openai, ollama
    ai_key_source: str = Field(default="platform")  # platform, tenant
    ai_provider_config: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    # Structure when ai_key_source="tenant":
    # {
    #   "claude": {"api_key_encrypted": "...", "model": "claude-3-sonnet-20240229"},
    #   "openai": {"api_key_encrypted": "...", "model": "gpt-4-turbo"},
    #   "azure_openai": {
    #       "api_key_encrypted": "...",
    #       "endpoint": "https://xxx.openai.azure.com",
    #       "deployment": "gpt-4",
    #       "api_version": "2024-02-15-preview"
    #   },
    #   "ollama": {"base_url": "http://localhost:11434", "model": "llama2"}
    # }

    # AI usage limits (for platform key users)
    ai_monthly_token_limit: int | None = Field(default=None)  # None = unlimited (enterprise)
    ai_tokens_used_this_month: int = Field(default=0)

    # Tenant settings
    settings: dict = Field(default_factory=dict, sa_column=Column(JSONB))

    # Microsoft 365 integration
    azure_tenant_id: str | None = Field(default=None, index=True)
    graph_subscription_id: str | None = Field(default=None)  # For webhook notifications

    # Relationships
    users: list["User"] = Relationship(back_populates="tenant")
    categories: list["Category"] = Relationship(back_populates="tenant")
    messages: list["Message"] = Relationship(back_populates="tenant")
    workflows: list["Workflow"] = Relationship(back_populates="tenant")
    contacts: list["Contact"] = Relationship(back_populates="tenant")
    custom_field_definitions: list["CustomFieldDefinition"] = Relationship(back_populates="tenant")
    forms: list["Form"] = Relationship(back_populates="tenant")
    campaigns: list["Campaign"] = Relationship(back_populates="tenant")
    api_keys: list["APIKey"] = Relationship(back_populates="tenant")
    list_of_values: list["ListOfValues"] = Relationship(back_populates="tenant")
    vote_histories: list["VoteHistory"] = Relationship(back_populates="tenant")
    jobs: list["Job"] = Relationship(back_populates="tenant")
    audit_logs: list["AuditLog"] = Relationship(back_populates="tenant")

    @model_validator(mode="before")
    @classmethod
    def validate_slug(cls, values: dict) -> dict:
        """Ensure slug is lowercase and URL-safe."""
        if "slug" in values and values["slug"]:
            values["slug"] = values["slug"].lower().replace(" ", "-")
        return values

    def uses_platform_key(self) -> bool:
        """Check if tenant uses Dewey's platform AI key."""
        return self.ai_key_source == "platform"

    def has_ai_budget_remaining(self) -> bool:
        """Check if tenant has remaining AI token budget (for platform key users)."""
        if self.ai_key_source == "tenant":
            return True  # Tenant's own key, no platform limits
        if self.ai_monthly_token_limit is None:
            return True  # Unlimited (enterprise)
        return self.ai_tokens_used_this_month < self.ai_monthly_token_limit


class TenantCreate(TenantBase):
    """Schema for creating a tenant."""

    pass


class TenantRead(TenantBase):
    """Schema for reading a tenant."""

    id: UUID
    marketplace_provider: str | None = None
    ai_provider: str


class TenantUpdate(SQLModel):
    """Schema for updating a tenant."""

    name: str | None = None
    subscription_tier: str | None = None
    ai_provider: str | None = None
    settings: dict | None = None
