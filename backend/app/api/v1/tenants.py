"""Tenant management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_session
from app.models.tenant import Tenant
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
