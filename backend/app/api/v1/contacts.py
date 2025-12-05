"""Contact management endpoints."""

from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select, func, update

from app.core.database import get_session
from app.api.v1.deps import PermissionChecker
from app.models.user import User, Permissions
from app.models.contact import (
    Contact,
    ContactCreate,
    ContactRead,
    ContactUpdate,
    ContactFieldValue,
    CustomFieldDefinition,
)
from app.models.message import Message
from app.models.analysis import Analysis

router = APIRouter()


class ContactListResponse(BaseModel):
    """Paginated contact list response."""

    items: list[ContactRead]
    total: int
    page: int
    page_size: int
    pages: int


class CustomFieldValueResponse(BaseModel):
    """Custom field value for response."""

    field_key: str
    field_name: str
    field_type: str
    value: str | float | bool | list[str] | None

    class Config:
        from_attributes = True


class ContactDetailResponse(ContactRead):
    """Contact with additional details."""

    notes: str | None = None
    custom_fields: list[CustomFieldValueResponse] = []


class MessageSummary(BaseModel):
    """Brief message info for contact messages list."""

    id: UUID
    subject: str
    sender_email: str
    source: str
    processing_status: str
    received_at: datetime
    sentiment_label: str | None = None

    class Config:
        from_attributes = True


class ContactMessagesResponse(BaseModel):
    """Paginated contact messages response."""

    items: list[MessageSummary]
    total: int
    page: int
    page_size: int
    pages: int


class ContactTimelineEntry(BaseModel):
    """Single entry in contact timeline."""

    date: str
    message_count: int
    avg_sentiment: float | None


class ContactTimelineResponse(BaseModel):
    """Contact sentiment/activity timeline."""

    contact_id: UUID
    entries: list[ContactTimelineEntry]


class BulkTagRequest(BaseModel):
    """Request for bulk tag operations."""

    contact_ids: list[UUID]
    tag: str


class BulkTagResponse(BaseModel):
    """Response for bulk tag operations."""

    success_count: int
    failed_count: int


# =============================================================================
# Contact Endpoints
# =============================================================================


@router.get("", response_model=ContactListResponse)
async def list_contacts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Search by email or name"),
    tag: str | None = Query(None, description="Filter by tag"),
    min_messages: int | None = Query(None, description="Minimum message count"),
    sentiment: str | None = Query(None, description="Filter by avg sentiment (positive/neutral/negative)"),
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

    # Apply min messages filter
    if min_messages:
        query = query.where(Contact.message_count >= min_messages)

    # Apply sentiment filter
    if sentiment:
        if sentiment == "positive":
            query = query.where(Contact.avg_sentiment > 0.3)
        elif sentiment == "negative":
            query = query.where(Contact.avg_sentiment < -0.3)
        elif sentiment == "neutral":
            query = query.where(Contact.avg_sentiment.between(-0.3, 0.3))

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
    """Get a specific contact by ID with full details including custom fields."""
    result = await session.execute(
        select(Contact)
        .where(
            Contact.id == contact_id,
            Contact.tenant_id == current_user.tenant_id,
        )
        .options(
            selectinload(Contact.field_values).selectinload(ContactFieldValue.field_definition)
        )
    )
    contact = result.scalars().first()

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    # Build custom fields response
    custom_fields = []
    for fv in contact.field_values:
        value = fv.get_value()
        custom_fields.append(
            CustomFieldValueResponse(
                field_key=fv.field_definition.field_key,
                field_name=fv.field_definition.name,
                field_type=fv.field_definition.field_type,
                value=value,
            )
        )

    return ContactDetailResponse(
        **ContactRead.model_validate(contact).model_dump(),
        notes=contact.notes,
        custom_fields=custom_fields,
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
        tags=request.tags or [],
        notes=request.notes,
        first_contact_at=datetime.utcnow(),
        last_contact_at=datetime.utcnow(),
    )
    session.add(contact)
    await session.flush()  # Get the contact ID

    # Handle custom fields
    if request.custom_fields:
        await _save_custom_field_values(
            session,
            current_user.tenant_id,
            contact.id,
            request.custom_fields,
        )

    await session.commit()
    await session.refresh(contact)

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

    # Handle custom fields updates
    if request.custom_fields is not None:
        await _save_custom_field_values(
            session,
            current_user.tenant_id,
            contact_id,
            request.custom_fields,
        )

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
        update(Message)
        .where(Message.contact_id == contact_id)
        .values(contact_id=None)
    )

    # Delete custom field values
    await session.execute(
        select(ContactFieldValue).where(ContactFieldValue.contact_id == contact_id)
    )
    # The cascade delete should handle field values, but let's be explicit
    field_values_result = await session.execute(
        select(ContactFieldValue).where(ContactFieldValue.contact_id == contact_id)
    )
    for fv in field_values_result.scalars().all():
        await session.delete(fv)

    await session.delete(contact)
    await session.commit()


@router.get("/{contact_id}/messages", response_model=ContactMessagesResponse)
async def get_contact_messages(
    contact_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(PermissionChecker(Permissions.CONTACTS_READ)),
    session: AsyncSession = Depends(get_session),
) -> ContactMessagesResponse:
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

    # Get messages with analysis for sentiment
    query = (
        select(Message)
        .where(Message.contact_id == contact_id)
        .options(selectinload(Message.analysis))
        .order_by(Message.received_at.desc())
    )

    # Get total count
    count_query = select(func.count()).select_from(
        select(Message).where(Message.contact_id == contact_id).subquery()
    )
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await session.execute(query)
    messages = result.scalars().all()

    pages = (total + page_size - 1) // page_size

    items = []
    for msg in messages:
        items.append(
            MessageSummary(
                id=msg.id,
                subject=msg.subject,
                sender_email=msg.sender_email,
                source=msg.source,
                processing_status=msg.processing_status,
                received_at=msg.received_at,
                sentiment_label=msg.analysis.sentiment_label if msg.analysis else None,
            )
        )

    return ContactMessagesResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


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

    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Query messages with analysis grouped by date
    query = (
        select(
            func.date_trunc("day", Message.received_at).label("date"),
            func.count(Message.id).label("message_count"),
            func.avg(Analysis.sentiment_score).label("avg_sentiment"),
        )
        .outerjoin(Analysis, Analysis.message_id == Message.id)
        .where(
            Message.contact_id == contact_id,
            Message.received_at >= start_date,
            Message.received_at <= end_date,
        )
        .group_by(func.date_trunc("day", Message.received_at))
        .order_by(func.date_trunc("day", Message.received_at))
    )

    result = await session.execute(query)
    rows = result.all()

    entries = []
    for row in rows:
        entries.append(
            ContactTimelineEntry(
                date=row.date.strftime("%Y-%m-%d") if row.date else "",
                message_count=row.message_count or 0,
                avg_sentiment=float(row.avg_sentiment) if row.avg_sentiment else None,
            )
        )

    return ContactTimelineResponse(
        contact_id=contact_id,
        entries=entries,
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


@router.post("/bulk-tag", response_model=BulkTagResponse)
async def bulk_add_tag(
    request: BulkTagRequest,
    current_user: User = Depends(PermissionChecker(Permissions.CONTACTS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> BulkTagResponse:
    """Add a tag to multiple contacts at once."""
    success_count = 0
    failed_count = 0

    for contact_id in request.contact_ids:
        result = await session.execute(
            select(Contact).where(
                Contact.id == contact_id,
                Contact.tenant_id == current_user.tenant_id,
            )
        )
        contact = result.scalars().first()

        if contact:
            if request.tag not in contact.tags:
                contact.tags = contact.tags + [request.tag]
            success_count += 1
        else:
            failed_count += 1

    await session.commit()

    return BulkTagResponse(
        success_count=success_count,
        failed_count=failed_count,
    )


@router.post("/merge")
async def merge_contacts(
    source_contact_ids: list[UUID],
    target_contact_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.CONTACTS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> ContactRead:
    """
    Merge multiple contacts into one.

    All messages from source contacts are moved to the target contact.
    Source contacts are deleted after merge.
    """
    # Verify target contact exists
    target_result = await session.execute(
        select(Contact).where(
            Contact.id == target_contact_id,
            Contact.tenant_id == current_user.tenant_id,
        )
    )
    target_contact = target_result.scalars().first()

    if not target_contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target contact not found",
        )

    total_messages_moved = 0

    for source_id in source_contact_ids:
        if source_id == target_contact_id:
            continue

        source_result = await session.execute(
            select(Contact).where(
                Contact.id == source_id,
                Contact.tenant_id == current_user.tenant_id,
            )
        )
        source_contact = source_result.scalars().first()

        if not source_contact:
            continue

        # Move messages to target
        await session.execute(
            update(Message)
            .where(Message.contact_id == source_id)
            .values(contact_id=target_contact_id)
        )

        total_messages_moved += source_contact.message_count or 0

        # Merge tags
        for tag in source_contact.tags:
            if tag not in target_contact.tags:
                target_contact.tags = target_contact.tags + [tag]

        # Delete source contact field values
        field_values_result = await session.execute(
            select(ContactFieldValue).where(ContactFieldValue.contact_id == source_id)
        )
        for fv in field_values_result.scalars().all():
            await session.delete(fv)

        # Delete source contact
        await session.delete(source_contact)

    # Update target contact stats
    target_contact.message_count = (target_contact.message_count or 0) + total_messages_moved

    await session.commit()
    await session.refresh(target_contact)

    return ContactRead.model_validate(target_contact)


# =============================================================================
# Helper Functions
# =============================================================================


async def _save_custom_field_values(
    session: AsyncSession,
    tenant_id: UUID,
    contact_id: UUID,
    custom_fields: dict,
) -> None:
    """Save or update custom field values for a contact."""
    # Get field definitions for this tenant
    field_defs_result = await session.execute(
        select(CustomFieldDefinition).where(
            CustomFieldDefinition.tenant_id == tenant_id
        )
    )
    field_defs = {fd.field_key: fd for fd in field_defs_result.scalars().all()}

    for field_key, value in custom_fields.items():
        if field_key not in field_defs:
            continue  # Skip unknown fields

        field_def = field_defs[field_key]

        # Check if value already exists
        existing_result = await session.execute(
            select(ContactFieldValue).where(
                ContactFieldValue.contact_id == contact_id,
                ContactFieldValue.field_definition_id == field_def.id,
            )
        )
        existing = existing_result.scalars().first()

        if existing:
            field_value = existing
        else:
            field_value = ContactFieldValue(
                contact_id=contact_id,
                field_definition_id=field_def.id,
            )
            session.add(field_value)

        # Set the appropriate value column based on field type
        if field_def.field_type == "text":
            field_value.value_text = str(value) if value else None
        elif field_def.field_type == "select":
            field_value.value_option = str(value) if value else None
        elif field_def.field_type == "multi_select":
            field_value.value_options = list(value) if value else None
        elif field_def.field_type == "number":
            field_value.value_number = float(value) if value else None
        elif field_def.field_type == "date":
            field_value.value_date = value if value else None
        elif field_def.field_type == "boolean":
            field_value.value_boolean = bool(value) if value is not None else None
