"""Role and user management schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Role Schemas
# =============================================================================


class RoleCreate(BaseModel):
    """Schema for creating a custom role."""

    name: str = Field(min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=255)
    permissions: list[str] = Field(default_factory=list)
    azure_ad_group_id: str | None = Field(default=None, max_length=255)


class RoleUpdate(BaseModel):
    """Schema for updating a role."""

    name: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=255)
    permissions: list[str] | None = None
    azure_ad_group_id: str | None = None


class RoleResponse(BaseModel):
    """Schema for role response."""

    id: UUID
    name: str
    description: str | None
    is_system: bool
    permissions: list[str]
    azure_ad_group_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RoleListResponse(BaseModel):
    """Schema for listing roles."""

    roles: list[RoleResponse]
    total: int


# =============================================================================
# User Management Schemas
# =============================================================================


class UserRoleAssignment(BaseModel):
    """Schema for assigning a role to a user."""

    role_id: UUID


class UserRoleResponse(BaseModel):
    """Schema for user role response."""

    role_id: UUID
    role_name: str
    assigned_at: datetime
    assigned_by: UUID | None


class UserListItem(BaseModel):
    """Schema for user in list view."""

    id: UUID
    email: str
    name: str
    is_active: bool
    azure_ad_oid: str | None
    roles: list[str]
    created_at: datetime
    last_login_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """Schema for listing users."""

    users: list[UserListItem]
    total: int


class UserDetailResponse(BaseModel):
    """Schema for detailed user response."""

    id: UUID
    email: str
    name: str
    is_active: bool
    azure_ad_oid: str | None
    tenant_id: UUID
    roles: list[UserRoleResponse]
    permissions: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    """Schema for updating a user."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None


class InviteUserRequest(BaseModel):
    """Schema for inviting a new user."""

    email: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    role_ids: list[UUID] = Field(default_factory=list)


# =============================================================================
# Permission Schemas
# =============================================================================


class PermissionInfo(BaseModel):
    """Schema for permission information."""

    key: str
    name: str
    description: str
    category: str


class PermissionListResponse(BaseModel):
    """Schema for listing available permissions."""

    permissions: list[PermissionInfo]
