"""Custom field definition management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_session
from app.api.v1.deps import PermissionChecker
from app.models.user import User, Permissions
from app.models.contact import (
    CustomFieldDefinition,
    CustomFieldCreate,
    CustomFieldRead,
    ContactFieldValue,
)

router = APIRouter()


class CustomFieldListResponse(BaseModel):
    """Custom field list response."""

    items: list[CustomFieldRead]
    total: int


class CustomFieldUpdate(BaseModel):
    """Schema for updating a custom field definition."""

    name: str | None = None
    options: list[dict] | None = None
    is_required: bool | None = None
    is_searchable: bool | None = None
    is_visible_in_list: bool | None = None
    sort_order: int | None = None


# =============================================================================
# Custom Field Definition Endpoints
# =============================================================================


@router.get("", response_model=CustomFieldListResponse)
async def list_custom_fields(
    current_user: User = Depends(PermissionChecker(Permissions.SETTINGS_READ)),
    session: AsyncSession = Depends(get_session),
) -> CustomFieldListResponse:
    """List all custom field definitions for the current tenant."""
    result = await session.execute(
        select(CustomFieldDefinition)
        .where(CustomFieldDefinition.tenant_id == current_user.tenant_id)
        .order_by(CustomFieldDefinition.sort_order, CustomFieldDefinition.name)
    )
    fields = result.scalars().all()

    return CustomFieldListResponse(
        items=[CustomFieldRead.model_validate(f) for f in fields],
        total=len(fields),
    )


@router.get("/{field_id}", response_model=CustomFieldRead)
async def get_custom_field(
    field_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.SETTINGS_READ)),
    session: AsyncSession = Depends(get_session),
) -> CustomFieldRead:
    """Get a specific custom field definition by ID."""
    result = await session.execute(
        select(CustomFieldDefinition).where(
            CustomFieldDefinition.id == field_id,
            CustomFieldDefinition.tenant_id == current_user.tenant_id,
        )
    )
    field = result.scalars().first()

    if not field:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom field not found",
        )

    return CustomFieldRead.model_validate(field)


@router.post("", response_model=CustomFieldRead, status_code=status.HTTP_201_CREATED)
async def create_custom_field(
    request: CustomFieldCreate,
    current_user: User = Depends(PermissionChecker(Permissions.SETTINGS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> CustomFieldRead:
    """
    Create a new custom field definition.

    Custom fields allow tenants to track additional contact attributes
    specific to their needs (e.g., party affiliation, district, customer tier).
    """
    # Check for duplicate field_key within tenant
    result = await session.execute(
        select(CustomFieldDefinition).where(
            CustomFieldDefinition.tenant_id == current_user.tenant_id,
            CustomFieldDefinition.field_key == request.field_key,
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Custom field with this key already exists",
        )

    # Validate options for select/multi_select fields
    if request.field_type in ("select", "multi_select") and not request.options:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select and multi_select fields require options",
        )

    field = CustomFieldDefinition(
        tenant_id=current_user.tenant_id,
        **request.model_dump(),
    )
    session.add(field)
    await session.commit()
    await session.refresh(field)

    return CustomFieldRead.model_validate(field)


@router.patch("/{field_id}", response_model=CustomFieldRead)
async def update_custom_field(
    field_id: UUID,
    request: CustomFieldUpdate,
    current_user: User = Depends(PermissionChecker(Permissions.SETTINGS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> CustomFieldRead:
    """
    Update a custom field definition.

    Note: field_key and field_type cannot be changed after creation
    as this would invalidate existing data.
    """
    result = await session.execute(
        select(CustomFieldDefinition).where(
            CustomFieldDefinition.id == field_id,
            CustomFieldDefinition.tenant_id == current_user.tenant_id,
        )
    )
    field = result.scalars().first()

    if not field:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom field not found",
        )

    # Apply updates
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(field, key, value)

    await session.commit()
    await session.refresh(field)

    return CustomFieldRead.model_validate(field)


@router.delete("/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_field(
    field_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.SETTINGS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Delete a custom field definition.

    Warning: This also deletes all values stored for this field across all contacts.
    """
    result = await session.execute(
        select(CustomFieldDefinition).where(
            CustomFieldDefinition.id == field_id,
            CustomFieldDefinition.tenant_id == current_user.tenant_id,
        )
    )
    field = result.scalars().first()

    if not field:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom field not found",
        )

    # Delete all field values for this definition
    field_values_result = await session.execute(
        select(ContactFieldValue).where(
            ContactFieldValue.field_definition_id == field_id
        )
    )
    for fv in field_values_result.scalars().all():
        await session.delete(fv)

    await session.delete(field)
    await session.commit()


@router.post("/{field_id}/reorder", response_model=CustomFieldRead)
async def reorder_custom_field(
    field_id: UUID,
    new_sort_order: int,
    current_user: User = Depends(PermissionChecker(Permissions.SETTINGS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> CustomFieldRead:
    """Change the display order of a custom field."""
    result = await session.execute(
        select(CustomFieldDefinition).where(
            CustomFieldDefinition.id == field_id,
            CustomFieldDefinition.tenant_id == current_user.tenant_id,
        )
    )
    field = result.scalars().first()

    if not field:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom field not found",
        )

    field.sort_order = new_sort_order
    await session.commit()
    await session.refresh(field)

    return CustomFieldRead.model_validate(field)
