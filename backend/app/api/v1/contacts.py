"""Contact management endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func

from app.core.database import get_session
from app.api.v1.deps import PermissionChecker
from app.models.user import User, Permissions
from app.models.contact import (
    Contact,
    ContactCreate,
    ContactRead,
    ContactUpdate,
)
from app.models.message import Message

router = APIRouter()


class ContactListResponse(BaseModel):
    """Paginated contact list response."""

    items: list[ContactRead]
    total: int
    page: int
    page_size: int
    pages: int


class ContactDetailResponse(ContactRead):
    """Contact with additional details."""

    notes: str | None = None
    custom_fields: dict | None = None


class ContactTimelineEntry(BaseModel):
    """Single entry in contact timeline."""

    date: datetime
    message_count: int
    avg_sentiment: float | None


class ContactTimelineResponse(BaseModel):
    """Contact sentiment/activity timeline."""

    contact_id: UUID
    entries: list[ContactTimelineEntry]


# =============================================================================
# Contact Endpoints
# =============================================================================


@router.get("", response_model=ContactListResponse)
async def list_contacts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Search by email or name"),
    tag: str | None = Query(None, description="Filter by tag"),
    sort_by: str = Query("last_contact_at", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(PermissionChecker(Permissions.CONTACTS_READ)),
    session: AsyncSession = Depends(get_session),
) -> ContactListResponse:
    """
    List contacts with pagination and filters.

    Supports searching by email/name and filtering by tags.
    """
    query = select(Contact).where(Contact.tenant_id == current_user.tenant_id)

    # Apply search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (Contact.email.ilike(search_pattern)) | (Contact.name.ilike(search_pattern))
        )

    # Apply tag filter
    if tag:
        query = query.where(Contact.tags.contains([tag]))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Apply sorting
    sort_column = getattr(Contact, sort_by, Contact.last_contact_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await session.execute(query)
    contacts = result.scalars().all()

    pages = (total + page_size - 1) // page_size

    return ContactListResponse(
        items=[ContactRead.model_validate(c) for c in contacts],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{contact_id}", response_model=ContactDetailResponse)
async def get_contact(
    contact_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.CONTACTS_READ)),
    session: AsyncSession = Depends(get_session),
) -> ContactDetailResponse:
    """Get a specific contact by ID with full details."""
    result = await session.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.tenant_id == current_user.tenant_id,
        )
    )
    contact = result.scalars().first()

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    # TODO: Load custom field values
    return ContactDetailResponse(
        **ContactRead.model_validate(contact).model_dump(),
        notes=contact.notes,
        custom_fields=None,  # TODO: Load from ContactFieldValue
    )


@router.post("", response_model=ContactRead, status_code=status.HTTP_201_CREATED)
async def create_contact(
    request: ContactCreate,
    current_user: User = Depends(PermissionChecker(Permissions.CONTACTS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> ContactRead:
    """
    Create a new contact.

    Contacts are usually auto-created from messages, but can be manually created.
    """
    # Check for duplicate email within tenant
    result = await session.execute(
        select(Contact).where(
            Contact.tenant_id == current_user.tenant_id,
            Contact.email == request.email,
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contact with this email already exists",
        )

    contact = Contact(
        tenant_id=current_user.tenant_id,
        email=request.email,
        name=request.name,
        phone=request.phone,
        address=request.address,
        tags=request.tags,
        notes=request.notes,
        first_contact_at=datetime.utcnow(),
        last_contact_at=datetime.utcnow(),
    )
    session.add(contact)
    await session.commit()
    await session.refresh(contact)

    # TODO: Handle custom_fields from request

    return ContactRead.model_validate(contact)


@router.patch("/{contact_id}", response_model=ContactRead)
async def update_contact(
    contact_id: UUID,
    request: ContactUpdate,
    current_user: User = Depends(PermissionChecker(Permissions.CONTACTS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> ContactRead:
    """Update a contact's information."""
    result = await session.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.tenant_id == current_user.tenant_id,
        )
    )
    contact = result.scalars().first()

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    # Apply updates (excluding custom_fields which needs special handling)
    update_data = request.model_dump(exclude_unset=True, exclude={"custom_fields"})
    for field, value in update_data.items():
        setattr(contact, field, value)

    # TODO: Handle custom_fields updates

    await session.commit()
    await session.refresh(contact)

    return ContactRead.model_validate(contact)


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.CONTACTS_DELETE)),
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Delete a contact.

    Note: This does not delete associated messages, only the contact record.
    Messages will have their contact_id set to null.
    """
    result = await session.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.tenant_id == current_user.tenant_id,
        )
    )
    contact = result.scalars().first()

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    # Unlink messages from this contact
    await session.execute(
        select(Message).where(Message.contact_id == contact_id)
    )
    # TODO: Update messages to set contact_id = null

    await session.delete(contact)
    await session.commit()


@router.get("/{contact_id}/messages")
async def get_contact_messages(
    contact_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(PermissionChecker(Permissions.CONTACTS_READ)),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get all messages from a specific contact."""
    # Verify contact exists and belongs to tenant
    contact_result = await session.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.tenant_id == current_user.tenant_id,
        )
    )
    if not contact_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    # Get messages
    query = (
        select(Message)
        .where(Message.contact_id == contact_id)
        .order_by(Message.received_at.desc())
    )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await session.execute(query)
    messages = result.scalars().all()

    pages = (total + page_size - 1) // page_size

    return {
        "items": messages,  # TODO: Convert to MessageResponse schema
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.get("/{contact_id}/timeline", response_model=ContactTimelineResponse)
async def get_contact_timeline(
    contact_id: UUID,
    days: int = Query(30, ge=7, le=365, description="Number of days to include"),
    current_user: User = Depends(PermissionChecker(Permissions.CONTACTS_READ)),
    session: AsyncSession = Depends(get_session),
) -> ContactTimelineResponse:
    """
    Get sentiment/activity timeline for a contact.

    Returns daily aggregates of message count and average sentiment.
    """
    # Verify contact exists and belongs to tenant
    contact_result = await session.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.tenant_id == current_user.tenant_id,
        )
    )
    if not contact_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    # TODO: Implement timeline aggregation query
    # This requires joining with Analysis table and grouping by date

    return ContactTimelineResponse(
        contact_id=contact_id,
        entries=[],  # TODO: Populate with actual data
    )


@router.post("/{contact_id}/tags", response_model=ContactRead)
async def add_contact_tag(
    contact_id: UUID,
    tag: str = Query(..., min_length=1, max_length=50),
    current_user: User = Depends(PermissionChecker(Permissions.CONTACTS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> ContactRead:
    """Add a tag to a contact."""
    result = await session.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.tenant_id == current_user.tenant_id,
        )
    )
    contact = result.scalars().first()

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    if tag not in contact.tags:
        contact.tags = contact.tags + [tag]
        await session.commit()
        await session.refresh(contact)

    return ContactRead.model_validate(contact)


@router.delete("/{contact_id}/tags/{tag}", response_model=ContactRead)
async def remove_contact_tag(
    contact_id: UUID,
    tag: str,
    current_user: User = Depends(PermissionChecker(Permissions.CONTACTS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> ContactRead:
    """Remove a tag from a contact."""
    result = await session.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.tenant_id == current_user.tenant_id,
        )
    )
    contact = result.scalars().first()

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    if tag in contact.tags:
        contact.tags = [t for t in contact.tags if t != tag]
        await session.commit()
        await session.refresh(contact)

    return ContactRead.model_validate(contact)
