"""API Key management endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_session
from app.api.v1.deps import PermissionChecker
from app.models.user import User, Permissions
from app.models.api_key import (
    APIKey,
    APIKeyCreate,
    APIKeyRead,
    APIKeyCreateResponse,
    APIKeyUpdate,
    APIScopes,
)

router = APIRouter()


# =============================================================================
# Scope Metadata
# =============================================================================

SCOPE_METADATA = {
    APIScopes.MESSAGES_READ: {
        "name": "Read Messages",
        "description": "View messages and their analysis",
    },
    APIScopes.MESSAGES_WRITE: {
        "name": "Write Messages",
        "description": "Submit new messages via API",
    },
    APIScopes.CONTACTS_READ: {
        "name": "Read Contacts",
        "description": "View contact information",
    },
    APIScopes.CONTACTS_WRITE: {
        "name": "Write Contacts",
        "description": "Create and update contacts",
    },
    APIScopes.CATEGORIES_READ: {
        "name": "Read Categories",
        "description": "View categories",
    },
    APIScopes.ANALYTICS_READ: {
        "name": "Read Analytics",
        "description": "Access analytics data (Power BI integration)",
    },
    APIScopes.ANALYTICS_EXPORT: {
        "name": "Export Analytics",
        "description": "Export analytics data in bulk",
    },
    APIScopes.FORMS_READ: {
        "name": "Read Forms",
        "description": "View form definitions",
    },
    APIScopes.FORMS_SUBMIT: {
        "name": "Submit Forms",
        "description": "Submit form responses",
    },
    APIScopes.CAMPAIGNS_READ: {
        "name": "Read Campaigns",
        "description": "View detected campaigns",
    },
    APIScopes.WEBHOOKS_RECEIVE: {
        "name": "Receive Webhooks",
        "description": "Receive webhook notifications",
    },
}


# =============================================================================
# API Key Endpoints
# =============================================================================


@router.get("/scopes")
async def list_scopes() -> dict:
    """
    List all available API key scopes.

    Returns metadata about each scope for UI display.
    """
    scopes = [
        {
            "key": key,
            "name": meta["name"],
            "description": meta["description"],
        }
        for key, meta in SCOPE_METADATA.items()
    ]
    return {"scopes": scopes}


@router.get("", response_model=list[APIKeyRead])
async def list_api_keys(
    current_user: User = Depends(PermissionChecker(Permissions.API_KEYS_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> list[APIKeyRead]:
    """
    List all API keys for the current tenant.

    Note: Full keys are never returned - only the prefix for identification.
    """
    result = await session.execute(
        select(APIKey)
        .where(APIKey.tenant_id == current_user.tenant_id)
        .order_by(APIKey.created_at.desc())
    )
    keys = result.scalars().all()

    return [APIKeyRead.model_validate(key) for key in keys]


@router.get("/{key_id}", response_model=APIKeyRead)
async def get_api_key(
    key_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.API_KEYS_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> APIKeyRead:
    """
    Get a specific API key by ID.
    """
    result = await session.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.tenant_id == current_user.tenant_id,
        )
    )
    key = result.scalars().first()

    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    return APIKeyRead.model_validate(key)


@router.post("", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: APIKeyCreate,
    current_user: User = Depends(PermissionChecker(Permissions.API_KEYS_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> APIKeyCreateResponse:
    """
    Create a new API key.

    IMPORTANT: The full API key is only returned once in this response.
    Store it securely - it cannot be retrieved again.
    """
    # Validate scopes
    valid_scopes = set(SCOPE_METADATA.keys())
    invalid_scopes = set(request.scopes) - valid_scopes - {"*"}
    if invalid_scopes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scopes: {', '.join(invalid_scopes)}",
        )

    # Generate the key
    full_key, key_hash, key_prefix = APIKey.generate_key()

    # Create the API key record
    api_key = APIKey(
        tenant_id=current_user.tenant_id,
        name=request.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        scopes=request.scopes,
        rate_limit=request.rate_limit,
        expires_at=request.expires_at,
        allowed_ips=request.allowed_ips,
    )
    session.add(api_key)
    await session.commit()
    await session.refresh(api_key)

    # Return response with the full key (only time it's available)
    response_data = APIKeyRead.model_validate(api_key).model_dump()
    response_data["key"] = full_key

    return APIKeyCreateResponse(**response_data)


@router.patch("/{key_id}", response_model=APIKeyRead)
async def update_api_key(
    key_id: UUID,
    request: APIKeyUpdate,
    current_user: User = Depends(PermissionChecker(Permissions.API_KEYS_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> APIKeyRead:
    """
    Update an API key's metadata, scopes, or restrictions.

    Note: The key itself cannot be changed - create a new key if needed.
    """
    result = await session.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.tenant_id == current_user.tenant_id,
        )
    )
    api_key = result.scalars().first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    # Validate scopes if provided
    if request.scopes is not None:
        valid_scopes = set(SCOPE_METADATA.keys())
        invalid_scopes = set(request.scopes) - valid_scopes - {"*"}
        if invalid_scopes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid scopes: {', '.join(invalid_scopes)}",
            )
        api_key.scopes = request.scopes

    # Update other fields
    if request.name is not None:
        api_key.name = request.name
    if request.rate_limit is not None:
        api_key.rate_limit = request.rate_limit
    if request.expires_at is not None:
        api_key.expires_at = request.expires_at
    if request.allowed_ips is not None:
        api_key.allowed_ips = request.allowed_ips if request.allowed_ips else None

    await session.commit()
    await session.refresh(api_key)

    return APIKeyRead.model_validate(api_key)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.API_KEYS_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Revoke (delete) an API key.

    This immediately invalidates the key - any requests using it will fail.
    """
    result = await session.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.tenant_id == current_user.tenant_id,
        )
    )
    api_key = result.scalars().first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    await session.delete(api_key)
    await session.commit()


@router.post("/{key_id}/rotate", response_model=APIKeyCreateResponse)
async def rotate_api_key(
    key_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.API_KEYS_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> APIKeyCreateResponse:
    """
    Rotate an API key - generates a new key while preserving settings.

    The old key is immediately invalidated. The new key is returned once.
    """
    result = await session.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.tenant_id == current_user.tenant_id,
        )
    )
    old_key = result.scalars().first()

    if not old_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    # Generate new key
    full_key, key_hash, key_prefix = APIKey.generate_key()

    # Update the key record with new hash/prefix
    old_key.key_hash = key_hash
    old_key.key_prefix = key_prefix
    old_key.last_used_at = None  # Reset usage tracking
    old_key.usage_count = 0

    await session.commit()
    await session.refresh(old_key)

    # Return response with the new full key
    response_data = APIKeyRead.model_validate(old_key).model_dump()
    response_data["key"] = full_key

    return APIKeyCreateResponse(**response_data)
