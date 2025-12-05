"""Message management endpoints."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select, func

from app.core.database import get_session
from app.api.v1.deps import PermissionChecker
from app.models.user import User, Permissions
from app.models.message import Message, MessageRead
from app.models.analysis import Analysis, AnalysisRead
from app.models.category import MessageCategory, Category
from app.models.contact import Contact

router = APIRouter()


class MessageCreateRequest(BaseModel):
    """Message creation schema (API intake)."""

    sender_email: EmailStr
    sender_name: str | None = None
    subject: str
    body_text: str
    body_html: str | None = None
    source: Literal["api", "form", "email", "upload"] = "api"
    source_metadata: dict | None = None
    attachments: list[dict] | None = None


class MessageResponse(BaseModel):
    """Message response schema."""

    id: UUID
    tenant_id: UUID
    sender_email: str
    sender_name: str | None
    subject: str
    body_text: str
    source: str
    processing_status: str
    is_template_match: bool
    received_at: datetime
    processed_at: datetime | None
    contact_id: UUID | None = None
    campaign_id: UUID | None = None

    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    """Paginated message list response."""

    items: list[MessageResponse]
    total: int
    page: int
    page_size: int
    pages: int


class AnalysisResponse(BaseModel):
    """Message analysis response."""

    id: UUID
    message_id: UUID
    sentiment_score: float
    sentiment_label: str
    sentiment_confidence: float
    summary: str
    entities: list[dict]
    suggested_categories: list[dict]
    suggested_response: str | None
    urgency_score: float
    ai_provider: str
    ai_model: str

    class Config:
        from_attributes = True


class CategoryInfo(BaseModel):
    """Category info for message detail."""

    id: UUID
    name: str
    color: str
    confidence: float | None
    is_ai_suggested: bool

    class Config:
        from_attributes = True


class MessageDetailResponse(MessageResponse):
    """Message detail with analysis and categories."""

    body_html: str | None = None
    attachments: list[dict] = []
    source_metadata: dict = {}
    template_similarity_score: float | None = None
    analysis: AnalysisResponse | None = None
    categories: list[CategoryInfo] = []


class MessageUpdateRequest(BaseModel):
    """Message update schema."""

    processing_status: Literal["pending", "processing", "completed", "failed"] | None = None


class BulkActionRequest(BaseModel):
    """Request for bulk message actions."""

    message_ids: list[UUID]
    action: Literal["categorize", "mark_processed", "delete"]
    category_id: UUID | None = None  # For categorize action


class BulkActionResponse(BaseModel):
    """Response for bulk actions."""

    success_count: int
    failed_count: int
    errors: list[dict] = []


# =============================================================================
# Message Endpoints
# =============================================================================


@router.post("", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    request: MessageCreateRequest,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """
    Submit a new message via API.

    This creates a message and queues it for AI processing.
    """
    tenant_id = current_user.tenant_id

    # Check if contact exists, create if not
    contact = None
    contact_result = await session.execute(
        select(Contact).where(
            Contact.tenant_id == tenant_id,
            Contact.email == request.sender_email,
        )
    )
    contact = contact_result.scalars().first()

    if not contact:
        contact = Contact(
            tenant_id=tenant_id,
            email=request.sender_email,
            name=request.sender_name,
            source="email",
            first_contact_at=datetime.utcnow(),
            last_contact_at=datetime.utcnow(),
            message_count=0,
        )
        session.add(contact)
        await session.flush()  # Get the contact ID

    # Create the message
    message = Message(
        tenant_id=tenant_id,
        contact_id=contact.id,
        sender_email=request.sender_email,
        sender_name=request.sender_name,
        subject=request.subject,
        body_text=request.body_text,
        body_html=request.body_html,
        source=request.source,
        source_metadata=request.source_metadata or {},
        attachments=request.attachments or [],
        processing_status="pending",
        received_at=datetime.utcnow(),
    )
    session.add(message)

    # Update contact stats
    contact.last_contact_at = datetime.utcnow()
    contact.message_count = (contact.message_count or 0) + 1

    await session.commit()
    await session.refresh(message)

    # TODO: Queue message for AI processing

    return MessageResponse.model_validate(message)


@router.get("", response_model=MessageListResponse)
async def list_messages(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source: str | None = Query(None, description="Filter by source (email, form, api, upload)"),
    sentiment: str | None = Query(None, description="Filter by sentiment label"),
    category_id: UUID | None = Query(None, description="Filter by category"),
    processing_status: str | None = Query(None, description="Filter by processing status"),
    is_template_match: bool | None = Query(None, description="Filter campaign messages"),
    search: str | None = Query(None, description="Search in subject and body"),
    date_from: datetime | None = Query(None, description="Filter messages after this date"),
    date_to: datetime | None = Query(None, description="Filter messages before this date"),
    sort_by: str = Query("received_at", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_READ)),
    session: AsyncSession = Depends(get_session),
) -> MessageListResponse:
    """List messages with filters and pagination."""
    tenant_id = current_user.tenant_id

    query = select(Message).where(Message.tenant_id == tenant_id)

    # Apply filters
    if source:
        query = query.where(Message.source == source)

    if processing_status:
        query = query.where(Message.processing_status == processing_status)

    if is_template_match is not None:
        query = query.where(Message.is_template_match == is_template_match)

    if date_from:
        query = query.where(Message.received_at >= date_from)

    if date_to:
        query = query.where(Message.received_at <= date_to)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (Message.subject.ilike(search_pattern))
            | (Message.body_text.ilike(search_pattern))
        )

    # Filter by sentiment (requires join with Analysis)
    if sentiment:
        query = query.join(Analysis, Analysis.message_id == Message.id).where(
            Analysis.sentiment_label == sentiment
        )

    # Filter by category (requires join with MessageCategory)
    if category_id:
        query = query.join(MessageCategory, MessageCategory.message_id == Message.id).where(
            MessageCategory.category_id == category_id
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Apply sorting
    sort_column = getattr(Message, sort_by, Message.received_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await session.execute(query)
    messages = result.scalars().all()

    pages = (total + page_size - 1) // page_size

    return MessageListResponse(
        items=[MessageResponse.model_validate(m) for m in messages],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{message_id}", response_model=MessageDetailResponse)
async def get_message(
    message_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_READ)),
    session: AsyncSession = Depends(get_session),
) -> MessageDetailResponse:
    """Get message details with analysis and categories."""
    result = await session.execute(
        select(Message)
        .where(
            Message.id == message_id,
            Message.tenant_id == current_user.tenant_id,
        )
        .options(
            selectinload(Message.analysis),
            selectinload(Message.message_categories).selectinload(MessageCategory.category),
        )
    )
    message = result.scalars().first()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    # Build response
    response_data = {
        "id": message.id,
        "tenant_id": message.tenant_id,
        "sender_email": message.sender_email,
        "sender_name": message.sender_name,
        "subject": message.subject,
        "body_text": message.body_text,
        "body_html": message.body_html,
        "source": message.source,
        "processing_status": message.processing_status,
        "is_template_match": message.is_template_match,
        "template_similarity_score": message.template_similarity_score,
        "received_at": message.received_at,
        "processed_at": message.processed_at,
        "contact_id": message.contact_id,
        "campaign_id": message.campaign_id,
        "attachments": message.attachments,
        "source_metadata": message.source_metadata,
        "analysis": None,
        "categories": [],
    }

    # Add analysis if available
    if message.analysis:
        response_data["analysis"] = AnalysisResponse.model_validate(message.analysis)

    # Add categories
    for mc in message.message_categories:
        response_data["categories"].append(
            CategoryInfo(
                id=mc.category.id,
                name=mc.category.name,
                color=mc.category.color,
                confidence=mc.confidence,
                is_ai_suggested=mc.is_ai_suggested,
            )
        )

    return MessageDetailResponse(**response_data)


@router.patch("/{message_id}", response_model=MessageResponse)
async def update_message(
    message_id: UUID,
    request: MessageUpdateRequest,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """Update message status."""
    result = await session.execute(
        select(Message).where(
            Message.id == message_id,
            Message.tenant_id == current_user.tenant_id,
        )
    )
    message = result.scalars().first()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    # Apply updates
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(message, field, value)

    if request.processing_status == "completed" and not message.processed_at:
        message.processed_at = datetime.utcnow()

    await session.commit()
    await session.refresh(message)

    return MessageResponse.model_validate(message)


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a message."""
    result = await session.execute(
        select(Message).where(
            Message.id == message_id,
            Message.tenant_id == current_user.tenant_id,
        )
    )
    message = result.scalars().first()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    await session.delete(message)
    await session.commit()


@router.post("/{message_id}/categories/{category_id}", status_code=status.HTTP_201_CREATED)
async def add_message_category(
    message_id: UUID,
    category_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Assign a category to a message."""
    # Verify message exists and belongs to tenant
    message_result = await session.execute(
        select(Message).where(
            Message.id == message_id,
            Message.tenant_id == current_user.tenant_id,
        )
    )
    message = message_result.scalars().first()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    # Verify category exists and belongs to tenant
    category_result = await session.execute(
        select(Category).where(
            Category.id == category_id,
            Category.tenant_id == current_user.tenant_id,
        )
    )
    category = category_result.scalars().first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    # Check if already assigned
    existing = await session.execute(
        select(MessageCategory).where(
            MessageCategory.message_id == message_id,
            MessageCategory.category_id == category_id,
        )
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category already assigned to message",
        )

    # Create assignment
    message_category = MessageCategory(
        message_id=message_id,
        category_id=category_id,
        is_ai_suggested=False,
        assigned_by=current_user.id,
    )
    session.add(message_category)
    await session.commit()

    return {"message": "Category assigned successfully"}


@router.delete("/{message_id}/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_message_category(
    message_id: UUID,
    category_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Remove a category from a message."""
    # Verify message belongs to tenant
    message_result = await session.execute(
        select(Message).where(
            Message.id == message_id,
            Message.tenant_id == current_user.tenant_id,
        )
    )
    if not message_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    # Find and delete the assignment
    result = await session.execute(
        select(MessageCategory).where(
            MessageCategory.message_id == message_id,
            MessageCategory.category_id == category_id,
        )
    )
    message_category = result.scalars().first()

    if not message_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not assigned to message",
        )

    await session.delete(message_category)
    await session.commit()


@router.post("/bulk-action", response_model=BulkActionResponse)
async def bulk_action(
    request: BulkActionRequest,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> BulkActionResponse:
    """Perform bulk actions on messages."""
    success_count = 0
    failed_count = 0
    errors = []

    for message_id in request.message_ids:
        try:
            # Verify message belongs to tenant
            result = await session.execute(
                select(Message).where(
                    Message.id == message_id,
                    Message.tenant_id == current_user.tenant_id,
                )
            )
            message = result.scalars().first()

            if not message:
                failed_count += 1
                errors.append({"message_id": str(message_id), "error": "Not found"})
                continue

            if request.action == "mark_processed":
                message.processing_status = "completed"
                message.processed_at = datetime.utcnow()
                success_count += 1

            elif request.action == "delete":
                await session.delete(message)
                success_count += 1

            elif request.action == "categorize":
                if not request.category_id:
                    failed_count += 1
                    errors.append({"message_id": str(message_id), "error": "No category_id provided"})
                    continue

                # Verify category
                cat_result = await session.execute(
                    select(Category).where(
                        Category.id == request.category_id,
                        Category.tenant_id == current_user.tenant_id,
                    )
                )
                if not cat_result.scalars().first():
                    failed_count += 1
                    errors.append({"message_id": str(message_id), "error": "Category not found"})
                    continue

                # Check if already assigned
                existing = await session.execute(
                    select(MessageCategory).where(
                        MessageCategory.message_id == message_id,
                        MessageCategory.category_id == request.category_id,
                    )
                )
                if not existing.scalars().first():
                    message_category = MessageCategory(
                        message_id=message_id,
                        category_id=request.category_id,
                        is_ai_suggested=False,
                        assigned_by=current_user.id,
                    )
                    session.add(message_category)
                success_count += 1

        except Exception as e:
            failed_count += 1
            errors.append({"message_id": str(message_id), "error": str(e)})

    await session.commit()

    return BulkActionResponse(
        success_count=success_count,
        failed_count=failed_count,
        errors=errors,
    )


@router.post("/{message_id}/reprocess", status_code=status.HTTP_202_ACCEPTED)
async def reprocess_message(
    message_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Queue a message for reprocessing by AI."""
    result = await session.execute(
        select(Message).where(
            Message.id == message_id,
            Message.tenant_id == current_user.tenant_id,
        )
    )
    message = result.scalars().first()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    # Reset processing status
    message.processing_status = "pending"
    message.processed_at = None

    # Delete existing analysis if any
    analysis_result = await session.execute(
        select(Analysis).where(Analysis.message_id == message_id)
    )
    existing_analysis = analysis_result.scalars().first()
    if existing_analysis:
        await session.delete(existing_analysis)

    await session.commit()

    # TODO: Queue for AI processing

    return {
        "message_id": message_id,
        "status": "queued",
    }


# =============================================================================
# Email Webhook Endpoint
# =============================================================================


@router.post("/email", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def receive_email_webhook(
    email_data: dict,
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """
    Receive email via webhook (from email service or Graph API).

    Expected email_data structure:
    {
        "tenant_id": "uuid",
        "from": {"email": "sender@example.com", "name": "Sender Name"},
        "subject": "Email subject",
        "body_text": "Plain text body",
        "body_html": "<html>HTML body</html>",
        "headers": {...},
        "message_id": "original-message-id",
        "received_at": "2024-01-15T10:30:00Z"
    }
    """
    # Validate required fields
    required_fields = ["tenant_id", "from", "subject", "body_text"]
    for field in required_fields:
        if field not in email_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required field: {field}",
            )

    tenant_id = UUID(email_data["tenant_id"])
    sender_info = email_data["from"]
    sender_email = sender_info.get("email")
    sender_name = sender_info.get("name")

    if not sender_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing sender email",
        )

    # Find or create contact
    contact_result = await session.execute(
        select(Contact).where(
            Contact.tenant_id == tenant_id,
            Contact.email == sender_email,
        )
    )
    contact = contact_result.scalars().first()

    if not contact:
        contact = Contact(
            tenant_id=tenant_id,
            email=sender_email,
            name=sender_name,
            source="email",
            first_contact_at=datetime.utcnow(),
            last_contact_at=datetime.utcnow(),
            message_count=0,
        )
        session.add(contact)
        await session.flush()

    # Build source metadata from email headers
    source_metadata = {
        "email_headers": email_data.get("headers", {}),
        "email_message_id": email_data.get("message_id"),
        "email_in_reply_to": email_data.get("in_reply_to"),
        "email_references": email_data.get("references", []),
    }

    # Create message
    message = Message(
        tenant_id=tenant_id,
        contact_id=contact.id,
        external_id=email_data.get("message_id"),
        sender_email=sender_email,
        sender_name=sender_name,
        subject=email_data["subject"],
        body_text=email_data["body_text"],
        body_html=email_data.get("body_html"),
        source="email",
        source_metadata=source_metadata,
        attachments=email_data.get("attachments", []),
        processing_status="pending",
        received_at=datetime.fromisoformat(email_data["received_at"]) if email_data.get("received_at") else datetime.utcnow(),
    )
    session.add(message)

    # Update contact stats
    contact.last_contact_at = datetime.utcnow()
    contact.message_count = (contact.message_count or 0) + 1

    await session.commit()
    await session.refresh(message)

    # TODO: Queue for AI processing

    return MessageResponse.model_validate(message)
