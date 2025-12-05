"""List of Values (LOV) management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_session
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.models.lov import (
    ListOfValues,
    LOVCreate,
    LOVUpdate,
    LOVRead,
    LIST_TYPES,
    create_default_lov_entries,
)

router = APIRouter()


# =============================================================================
# List Type Metadata
# =============================================================================

LIST_TYPE_METADATA = {
    "prefix": {
        "name": "Name Prefixes",
        "description": "Title prefixes like Mr., Mrs., Dr.",
    },
    "pronoun": {
        "name": "Pronouns",
        "description": "Personal pronouns for contacts",
    },
    "language": {
        "name": "Languages",
        "description": "Preferred languages for communication",
    },
    "gender": {
        "name": "Genders",
        "description": "Gender identity options",
    },
    "marital_status": {
        "name": "Marital Status",
        "description": "Marital status options",
    },
    "education_level": {
        "name": "Education Levels",
        "description": "Educational attainment levels",
    },
    "income_bracket": {
        "name": "Income Brackets",
        "description": "Household income ranges",
    },
    "homeowner_status": {
        "name": "Homeowner Status",
        "description": "Home ownership status options",
    },
    "voter_status": {
        "name": "Voter Status",
        "description": "Voter registration status options",
    },
    "communication_pref": {
        "name": "Communication Preferences",
        "description": "Preferred contact methods",
    },
    "inactive_reason": {
        "name": "Inactive Reasons",
        "description": "Reasons why a contact is marked inactive",
    },
}


# =============================================================================
# LOV Endpoints
# =============================================================================


@router.get("/types")
async def list_types() -> dict:
    """
    List all available LOV types with metadata.

    Returns metadata about each list type for UI display.
    """
    types = [
        {
            "key": key,
            "name": meta["name"],
            "description": meta["description"],
        }
        for key, meta in LIST_TYPE_METADATA.items()
    ]
    return {"types": types}


@router.get("")
async def get_all_lov(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, list[LOVRead]]:
    """
    Get all LOV entries for the current tenant, grouped by list type.

    Returns all active and inactive entries for management purposes.
    """
    result = await session.execute(
        select(ListOfValues)
        .where(ListOfValues.tenant_id == current_user.tenant_id)
        .order_by(ListOfValues.list_type, ListOfValues.sort_order)
    )
    entries = result.scalars().all()

    # Group by list_type
    grouped: dict[str, list[LOVRead]] = {lt: [] for lt in LIST_TYPES}
    for entry in entries:
        if entry.list_type in grouped:
            grouped[entry.list_type].append(LOVRead.model_validate(entry))

    return grouped


@router.get("/active")
async def get_active_lov(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, list[LOVRead]]:
    """
    Get only active LOV entries for the current tenant.

    This endpoint is optimized for form dropdowns - only returns active entries.
    """
    result = await session.execute(
        select(ListOfValues)
        .where(
            ListOfValues.tenant_id == current_user.tenant_id,
            ListOfValues.is_active == True,
        )
        .order_by(ListOfValues.list_type, ListOfValues.sort_order)
    )
    entries = result.scalars().all()

    # Group by list_type
    grouped: dict[str, list[LOVRead]] = {lt: [] for lt in LIST_TYPES}
    for entry in entries:
        if entry.list_type in grouped:
            grouped[entry.list_type].append(LOVRead.model_validate(entry))

    return grouped


@router.get("/{list_type}", response_model=list[LOVRead])
async def get_lov_by_type(
    list_type: str,
    active_only: bool = False,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[LOVRead]:
    """
    Get LOV entries for a specific list type.
    """
    if list_type not in LIST_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid list type: {list_type}. Valid types: {', '.join(LIST_TYPES)}",
        )

    query = select(ListOfValues).where(
        ListOfValues.tenant_id == current_user.tenant_id,
        ListOfValues.list_type == list_type,
    )

    if active_only:
        query = query.where(ListOfValues.is_active == True)

    query = query.order_by(ListOfValues.sort_order)

    result = await session.execute(query)
    entries = result.scalars().all()

    return [LOVRead.model_validate(entry) for entry in entries]


@router.post("/{list_type}", response_model=LOVRead, status_code=status.HTTP_201_CREATED)
async def create_lov_entry(
    list_type: str,
    request: LOVCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LOVRead:
    """
    Create a new LOV entry for a specific list type.
    """
    if list_type not in LIST_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid list type: {list_type}. Valid types: {', '.join(LIST_TYPES)}",
        )

    # Check for duplicate value
    existing = await session.execute(
        select(ListOfValues).where(
            ListOfValues.tenant_id == current_user.tenant_id,
            ListOfValues.list_type == list_type,
            ListOfValues.value == request.value,
        )
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Value '{request.value}' already exists for list type '{list_type}'",
        )

    # Get max sort_order for this list type
    max_order_result = await session.execute(
        select(ListOfValues.sort_order)
        .where(
            ListOfValues.tenant_id == current_user.tenant_id,
            ListOfValues.list_type == list_type,
        )
        .order_by(ListOfValues.sort_order.desc())
        .limit(1)
    )
    max_order = max_order_result.scalar() or -1

    entry = ListOfValues(
        tenant_id=current_user.tenant_id,
        list_type=list_type,
        value=request.value,
        label=request.label,
        sort_order=request.sort_order if request.sort_order > 0 else max_order + 1,
        is_active=request.is_active,
    )

    session.add(entry)
    await session.commit()
    await session.refresh(entry)

    return LOVRead.model_validate(entry)


@router.patch("/{entry_id}", response_model=LOVRead)
async def update_lov_entry(
    entry_id: UUID,
    request: LOVUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LOVRead:
    """
    Update an existing LOV entry.
    """
    result = await session.execute(
        select(ListOfValues).where(
            ListOfValues.id == entry_id,
            ListOfValues.tenant_id == current_user.tenant_id,
        )
    )
    entry = result.scalars().first()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LOV entry not found",
        )

    # Check for duplicate value if value is being changed
    if request.value is not None and request.value != entry.value:
        existing = await session.execute(
            select(ListOfValues).where(
                ListOfValues.tenant_id == current_user.tenant_id,
                ListOfValues.list_type == entry.list_type,
                ListOfValues.value == request.value,
                ListOfValues.id != entry_id,
            )
        )
        if existing.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Value '{request.value}' already exists for this list type",
            )

    # Update fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(entry, field, value)

    await session.commit()
    await session.refresh(entry)

    return LOVRead.model_validate(entry)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lov_entry(
    entry_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Delete an LOV entry.

    Consider using PATCH to set is_active=false instead of deleting,
    as this preserves historical data integrity.
    """
    result = await session.execute(
        select(ListOfValues).where(
            ListOfValues.id == entry_id,
            ListOfValues.tenant_id == current_user.tenant_id,
        )
    )
    entry = result.scalars().first()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LOV entry not found",
        )

    await session.delete(entry)
    await session.commit()


@router.post("/{list_type}/reorder", response_model=list[LOVRead])
async def reorder_lov_entries(
    list_type: str,
    entry_ids: list[UUID],
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[LOVRead]:
    """
    Reorder LOV entries by providing the list of entry IDs in the desired order.
    """
    if list_type not in LIST_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid list type: {list_type}. Valid types: {', '.join(LIST_TYPES)}",
        )

    # Fetch all entries for this list type
    result = await session.execute(
        select(ListOfValues).where(
            ListOfValues.tenant_id == current_user.tenant_id,
            ListOfValues.list_type == list_type,
        )
    )
    entries = {entry.id: entry for entry in result.scalars().all()}

    # Validate all IDs are present
    for i, entry_id in enumerate(entry_ids):
        if entry_id not in entries:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Entry ID {entry_id} not found in list type '{list_type}'",
            )
        entries[entry_id].sort_order = i

    await session.commit()

    # Return updated entries
    result = await session.execute(
        select(ListOfValues)
        .where(
            ListOfValues.tenant_id == current_user.tenant_id,
            ListOfValues.list_type == list_type,
        )
        .order_by(ListOfValues.sort_order)
    )
    updated_entries = result.scalars().all()

    return [LOVRead.model_validate(entry) for entry in updated_entries]


@router.post("/seed", response_model=dict)
async def seed_default_lov(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Seed default LOV entries for the current tenant.

    Only adds entries for list types that have no existing entries.
    This is useful for tenants created before the LOV system was implemented.
    """
    # Check which list types already have entries
    result = await session.execute(
        select(ListOfValues.list_type)
        .where(ListOfValues.tenant_id == current_user.tenant_id)
        .distinct()
    )
    existing_types = set(result.scalars().all())

    # Get default entries and filter out types that already exist
    all_entries = create_default_lov_entries(current_user.tenant_id)
    new_entries = [e for e in all_entries if e.list_type not in existing_types]

    if not new_entries:
        return {
            "message": "No new entries needed - all list types already have data",
            "seeded_count": 0,
            "list_types": [],
        }

    # Add new entries
    for entry in new_entries:
        session.add(entry)

    await session.commit()

    # Get list of seeded types
    seeded_types = list(set(e.list_type for e in new_entries))

    return {
        "message": f"Seeded {len(new_entries)} default LOV entries",
        "seeded_count": len(new_entries),
        "list_types": seeded_types,
    }
