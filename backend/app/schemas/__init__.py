"""Pydantic schemas for API requests and responses."""

from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    RefreshRequest,
    UserResponse,
    AzureAuthUrlResponse,
    AzureCallbackRequest,
    AzureLinkRequest,
)
from app.schemas.roles import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RoleListResponse,
    UserRoleAssignment,
    UserRoleResponse,
    UserListItem,
    UserListResponse,
    UserDetailResponse,
    UserUpdateRequest,
    InviteUserRequest,
    PermissionInfo,
    PermissionListResponse,
)

__all__ = [
    # Auth
    "LoginRequest",
    "RegisterRequest",
    "TokenResponse",
    "RefreshRequest",
    "UserResponse",
    "AzureAuthUrlResponse",
    "AzureCallbackRequest",
    "AzureLinkRequest",
    # Roles
    "RoleCreate",
    "RoleUpdate",
    "RoleResponse",
    "RoleListResponse",
    "UserRoleAssignment",
    "UserRoleResponse",
    "UserListItem",
    "UserListResponse",
    "UserDetailResponse",
    "UserUpdateRequest",
    "InviteUserRequest",
    "PermissionInfo",
    "PermissionListResponse",
]
