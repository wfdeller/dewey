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

__all__ = [
    "LoginRequest",
    "RegisterRequest",
    "TokenResponse",
    "RefreshRequest",
    "UserResponse",
    "AzureAuthUrlResponse",
    "AzureCallbackRequest",
    "AzureLinkRequest",
]
