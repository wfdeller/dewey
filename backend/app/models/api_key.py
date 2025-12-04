"""API Key model for service credentials."""

from datetime import datetime
from hashlib import sha256
from secrets import token_urlsafe
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Field, Relationship, SQLModel, String

from app.models.base import TenantBaseModel

if TYPE_CHECKING:
    from app.models.tenant import Tenant


class APIKeyBase(SQLModel):
    """API Key base schema."""

    name: str = Field(index=True)
    scopes: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String)))
    rate_limit: int = Field(default=100)  # Requests per minute


class APIKey(APIKeyBase, TenantBaseModel, table=True):
    """API Key database model for service credentials."""

    __tablename__ = "api_key"

    # Key storage (never store the full key)
    key_hash: str = Field(index=True)  # SHA-256 hash of the full key
    key_prefix: str = Field(index=True)  # First 8 chars for identification

    # Expiration
    expires_at: datetime | None = Field(default=None, index=True)

    # IP restrictions (optional)
    allowed_ips: list[str] | None = Field(default=None, sa_column=Column(ARRAY(String)))

    # Usage tracking
    last_used_at: datetime | None = Field(default=None)
    usage_count: int = Field(default=0)

    # Relationships
    tenant: "Tenant" = Relationship(back_populates="api_keys")

    @classmethod
    def generate_key(cls) -> tuple[str, str, str]:
        """
        Generate a new API key.

        Returns:
            Tuple of (full_key, key_hash, key_prefix)
            The full_key should only be shown once to the user.
        """
        # Generate a secure random key with prefix
        key = f"dwy_{token_urlsafe(32)}"
        key_hash = sha256(key.encode()).hexdigest()
        key_prefix = key[:12]  # "dwy_" + 8 chars
        return key, key_hash, key_prefix

    @classmethod
    def hash_key(cls, key: str) -> str:
        """Hash an API key for comparison."""
        return sha256(key.encode()).hexdigest()

    def is_expired(self) -> bool:
        """Check if the key is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def is_ip_allowed(self, ip_address: str) -> bool:
        """Check if the IP address is allowed."""
        if self.allowed_ips is None or len(self.allowed_ips) == 0:
            return True
        return ip_address in self.allowed_ips

    def has_scope(self, scope: str) -> bool:
        """Check if the key has a specific scope."""
        # Check for exact match or wildcard
        if scope in self.scopes:
            return True
        # Check for resource-level wildcard (e.g., "messages:*")
        resource = scope.split(":")[0]
        if f"{resource}:*" in self.scopes:
            return True
        # Check for full wildcard
        return "*" in self.scopes


# Available API scopes
class APIScopes:
    """Available API key scopes."""

    # Messages
    MESSAGES_READ = "messages:read"
    MESSAGES_WRITE = "messages:write"

    # Contacts
    CONTACTS_READ = "contacts:read"
    CONTACTS_WRITE = "contacts:write"

    # Categories
    CATEGORIES_READ = "categories:read"

    # Analytics (for Power BI integration)
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_EXPORT = "analytics:export"

    # Forms (for embedding)
    FORMS_READ = "forms:read"
    FORMS_SUBMIT = "forms:submit"

    # Campaigns
    CAMPAIGNS_READ = "campaigns:read"

    # Webhooks
    WEBHOOKS_RECEIVE = "webhooks:receive"


class APIKeyCreate(APIKeyBase):
    """Schema for creating an API key."""

    expires_at: datetime | None = None
    allowed_ips: list[str] | None = None


class APIKeyRead(APIKeyBase):
    """Schema for reading an API key."""

    id: UUID
    tenant_id: UUID
    key_prefix: str
    expires_at: datetime | None
    allowed_ips: list[str] | None
    last_used_at: datetime | None
    usage_count: int


class APIKeyCreateResponse(APIKeyRead):
    """Response when creating an API key (includes full key once)."""

    key: str  # Full key, only shown once


class APIKeyUpdate(SQLModel):
    """Schema for updating an API key."""

    name: str | None = None
    scopes: list[str] | None = None
    rate_limit: int | None = None
    expires_at: datetime | None = None
    allowed_ips: list[str] | None = None
