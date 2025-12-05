"""User and role models."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Column, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlmodel import Field, Relationship, SQLModel, String

from app.models.base import BaseModel, TenantBaseModel

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.job import Job
    from app.models.audit_log import AuditLog


class RoleBase(SQLModel):
    """Role base schema."""

    name: str = Field(index=True)
    description: str | None = None
    is_system: bool = Field(default=False)  # System roles cannot be deleted


class Role(RoleBase, TenantBaseModel, table=True):
    """Role database model for RBAC."""

    __tablename__ = "role"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_role_tenant_name"),)

    # Permissions as array of strings
    permissions: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String)))

    # Azure AD group sync
    azure_ad_group_id: str | None = Field(default=None, index=True)

    # Relationships
    user_roles: list["UserRole"] = Relationship(back_populates="role")


class UserBase(SQLModel):
    """User base schema."""

    email: str = Field(unique=True, index=True)
    name: str
    is_active: bool = Field(default=True)


class User(UserBase, TenantBaseModel, table=True):
    """User database model."""

    __tablename__ = "user"

    # Password hash (null for SSO-only users)
    password_hash: str | None = Field(default=None)

    # Azure AD integration
    azure_ad_oid: str | None = Field(default=None, index=True)  # Object ID from Azure AD

    # User preferences
    preferences: dict = Field(default_factory=dict, sa_column=Column(JSONB))

    # Relationships
    tenant: "Tenant" = Relationship(back_populates="users")
    user_roles: list["UserRole"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"foreign_keys": "UserRole.user_id"},
    )
    jobs: list["Job"] = Relationship(back_populates="created_by")
    audit_logs: list["AuditLog"] = Relationship(back_populates="user")

    @property
    def roles(self) -> list[Role]:
        """Get user's roles."""
        return [ur.role for ur in self.user_roles]

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        for user_role in self.user_roles:
            if permission in user_role.role.permissions:
                return True
        return False

    def has_any_permission(self, permissions: list[str]) -> bool:
        """Check if user has any of the specified permissions."""
        return any(self.has_permission(p) for p in permissions)


class UserRole(SQLModel, table=True):
    """User-Role association table."""

    __tablename__ = "user_role"

    user_id: UUID = Field(foreign_key="user.id", primary_key=True)
    role_id: UUID = Field(foreign_key="role.id", primary_key=True)
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    assigned_by: UUID | None = Field(default=None, foreign_key="user.id")

    # Relationships
    user: User = Relationship(
        back_populates="user_roles",
        sa_relationship_kwargs={"foreign_keys": "[UserRole.user_id]"},
    )
    role: Role = Relationship(back_populates="user_roles")


# Permission constants
class Permissions:
    """Permission constants for RBAC."""

    # Messages
    MESSAGES_READ = "messages:read"
    MESSAGES_WRITE = "messages:write"
    MESSAGES_DELETE = "messages:delete"
    MESSAGES_ASSIGN = "messages:assign"

    # Contacts
    CONTACTS_READ = "contacts:read"
    CONTACTS_WRITE = "contacts:write"
    CONTACTS_DELETE = "contacts:delete"

    # Categories
    CATEGORIES_READ = "categories:read"
    CATEGORIES_WRITE = "categories:write"

    # Workflows
    WORKFLOWS_READ = "workflows:read"
    WORKFLOWS_WRITE = "workflows:write"
    WORKFLOWS_EXECUTE = "workflows:execute"

    # Analytics
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_EXPORT = "analytics:export"

    # Forms
    FORMS_READ = "forms:read"
    FORMS_WRITE = "forms:write"

    # Campaigns
    CAMPAIGNS_READ = "campaigns:read"
    CAMPAIGNS_WRITE = "campaigns:write"

    # Settings
    SETTINGS_READ = "settings:read"
    SETTINGS_WRITE = "settings:write"

    # Users
    USERS_READ = "users:read"
    USERS_WRITE = "users:write"

    # Roles
    ROLES_WRITE = "roles:write"

    # API Keys
    API_KEYS_MANAGE = "api_keys:manage"

    # Integrations
    INTEGRATIONS_MANAGE = "integrations:manage"

    # Billing
    BILLING_MANAGE = "billing:manage"


# Default system roles
DEFAULT_ROLES = {
    "owner": {
        "description": "Full access to all features",
        "permissions": [
            Permissions.MESSAGES_READ,
            Permissions.MESSAGES_WRITE,
            Permissions.MESSAGES_DELETE,
            Permissions.MESSAGES_ASSIGN,
            Permissions.CONTACTS_READ,
            Permissions.CONTACTS_WRITE,
            Permissions.CONTACTS_DELETE,
            Permissions.CATEGORIES_READ,
            Permissions.CATEGORIES_WRITE,
            Permissions.WORKFLOWS_READ,
            Permissions.WORKFLOWS_WRITE,
            Permissions.WORKFLOWS_EXECUTE,
            Permissions.ANALYTICS_READ,
            Permissions.ANALYTICS_EXPORT,
            Permissions.FORMS_READ,
            Permissions.FORMS_WRITE,
            Permissions.CAMPAIGNS_READ,
            Permissions.CAMPAIGNS_WRITE,
            Permissions.SETTINGS_READ,
            Permissions.SETTINGS_WRITE,
            Permissions.USERS_READ,
            Permissions.USERS_WRITE,
            Permissions.ROLES_WRITE,
            Permissions.API_KEYS_MANAGE,
            Permissions.INTEGRATIONS_MANAGE,
            Permissions.BILLING_MANAGE,
        ],
    },
    "admin": {
        "description": "Administrative access without billing",
        "permissions": [
            Permissions.MESSAGES_READ,
            Permissions.MESSAGES_WRITE,
            Permissions.MESSAGES_DELETE,
            Permissions.MESSAGES_ASSIGN,
            Permissions.CONTACTS_READ,
            Permissions.CONTACTS_WRITE,
            Permissions.CONTACTS_DELETE,
            Permissions.CATEGORIES_READ,
            Permissions.CATEGORIES_WRITE,
            Permissions.WORKFLOWS_READ,
            Permissions.WORKFLOWS_WRITE,
            Permissions.WORKFLOWS_EXECUTE,
            Permissions.ANALYTICS_READ,
            Permissions.ANALYTICS_EXPORT,
            Permissions.FORMS_READ,
            Permissions.FORMS_WRITE,
            Permissions.CAMPAIGNS_READ,
            Permissions.CAMPAIGNS_WRITE,
            Permissions.SETTINGS_READ,
            Permissions.SETTINGS_WRITE,
            Permissions.USERS_READ,
            Permissions.USERS_WRITE,
            Permissions.ROLES_WRITE,
            Permissions.API_KEYS_MANAGE,
            Permissions.INTEGRATIONS_MANAGE,
        ],
    },
    "manager": {
        "description": "Team management and analytics",
        "permissions": [
            Permissions.MESSAGES_READ,
            Permissions.MESSAGES_WRITE,
            Permissions.MESSAGES_ASSIGN,
            Permissions.CONTACTS_READ,
            Permissions.CONTACTS_WRITE,
            Permissions.CATEGORIES_READ,
            Permissions.WORKFLOWS_READ,
            Permissions.WORKFLOWS_WRITE,
            Permissions.ANALYTICS_READ,
            Permissions.ANALYTICS_EXPORT,
            Permissions.FORMS_READ,
            Permissions.FORMS_WRITE,
            Permissions.CAMPAIGNS_READ,
            Permissions.CAMPAIGNS_WRITE,
            Permissions.USERS_READ,
        ],
    },
    "agent": {
        "description": "Handle messages and contacts",
        "permissions": [
            Permissions.MESSAGES_READ,
            Permissions.MESSAGES_WRITE,
            Permissions.CONTACTS_READ,
            Permissions.CONTACTS_WRITE,
            Permissions.CATEGORIES_READ,
            Permissions.WORKFLOWS_READ,
            Permissions.FORMS_READ,
            Permissions.CAMPAIGNS_READ,
        ],
    },
    "viewer": {
        "description": "Read-only access",
        "permissions": [
            Permissions.MESSAGES_READ,
            Permissions.CONTACTS_READ,
            Permissions.CATEGORIES_READ,
            Permissions.ANALYTICS_READ,
            Permissions.FORMS_READ,
            Permissions.CAMPAIGNS_READ,
        ],
    },
}


class UserCreate(UserBase):
    """Schema for creating a user."""

    password: str


class UserRead(UserBase):
    """Schema for reading a user."""

    id: UUID
    tenant_id: UUID
    azure_ad_oid: str | None = None


class UserUpdate(SQLModel):
    """Schema for updating a user."""

    name: str | None = None
    is_active: bool | None = None
    preferences: dict | None = None
