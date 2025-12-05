"""Tenant management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_session
from app.api.v1.deps import get_current_user
from app.models.tenant import Tenant
from app.models.user import User
from app.models.lov import create_default_lov_entries

router = APIRouter()


class TenantCreateRequest(BaseModel):
    """Tenant creation schema."""

    name: str
    slug: str


class TenantResponse(BaseModel):
    """Tenant response schema."""

    id: UUID
    name: str
    slug: str
    subscription_tier: str


class TenantUpdate(BaseModel):
    """Tenant update schema."""

    name: str | None = None
    settings: dict | None = None


class WorkerSettingsResponse(BaseModel):
    """Worker settings response."""

    max_concurrent_jobs: int = Field(default=1, ge=1, le=10)
    job_timeout_seconds: int = Field(default=3600, ge=60, le=14400)
    max_retries: int = Field(default=3, ge=0, le=10)


class WorkerSettingsUpdate(BaseModel):
    """Worker settings update schema."""

    max_concurrent_jobs: int | None = Field(default=None, ge=1, le=10)
    job_timeout_seconds: int | None = Field(default=None, ge=60, le=14400)
    max_retries: int | None = Field(default=None, ge=0, le=10)


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    request: TenantCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> TenantResponse:
    """Create a new tenant (marketplace provisioning)."""
    # Check if slug already exists
    existing = await session.execute(
        select(Tenant).where(Tenant.slug == request.slug.lower().replace(" ", "-"))
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tenant with slug '{request.slug}' already exists",
        )

    # Create tenant
    tenant = Tenant(
        name=request.name,
        slug=request.slug,
    )
    session.add(tenant)
    await session.flush()  # Get tenant ID

    # Seed default LOV entries
    lov_entries = create_default_lov_entries(tenant.id)
    for entry in lov_entries:
        session.add(entry)

    await session.commit()
    await session.refresh(tenant)

    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        subscription_tier=tenant.subscription_tier,
    )


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> TenantResponse:
    """Get tenant details."""
    # TODO: Implement tenant retrieval
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Tenant retrieval not yet implemented",
    )


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID,
    update: TenantUpdate,
    session: AsyncSession = Depends(get_session),
) -> TenantResponse:
    """Update tenant settings."""
    # TODO: Implement tenant update
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Tenant update not yet implemented",
    )


# =============================================================================
# Worker Settings Endpoints
# =============================================================================

# Default worker settings
DEFAULT_WORKER_SETTINGS = {
    "max_concurrent_jobs": 1,
    "job_timeout_seconds": 3600,
    "max_retries": 3,
}


@router.get("/settings/worker", response_model=WorkerSettingsResponse)
async def get_worker_settings(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WorkerSettingsResponse:
    """
    Get worker/job queue settings for the current tenant.

    Returns the configured worker settings with defaults applied.
    """
    # Get tenant
    result = await session.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalars().first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Merge defaults with tenant settings
    worker_settings = {
        **DEFAULT_WORKER_SETTINGS,
        **tenant.settings.get("worker", {}),
    }

    return WorkerSettingsResponse(**worker_settings)


@router.patch("/settings/worker", response_model=WorkerSettingsResponse)
async def update_worker_settings(
    settings_update: WorkerSettingsUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WorkerSettingsResponse:
    """
    Update worker/job queue settings for the current tenant.

    Only provided fields will be updated. Requires SETTINGS_WRITE permission.

    Note: Changes to max_concurrent_jobs require a worker restart to take effect.
    """
    # Check permission
    if "SETTINGS_WRITE" not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Settings write permission required",
        )

    # Get tenant
    result = await session.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalars().first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Get current worker settings or initialize
    current_settings = tenant.settings.get("worker", {})

    # Update only provided fields
    update_data = settings_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            current_settings[key] = value

    # Update tenant settings
    new_settings = {**tenant.settings, "worker": current_settings}
    tenant.settings = new_settings

    await session.commit()
    await session.refresh(tenant)

    # Return merged settings with defaults
    worker_settings = {
        **DEFAULT_WORKER_SETTINGS,
        **tenant.settings.get("worker", {}),
    }

    return WorkerSettingsResponse(**worker_settings)
