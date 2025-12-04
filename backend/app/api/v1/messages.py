"""Message management endpoints."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session

router = APIRouter()


class MessageCreate(BaseModel):
    """Message creation schema (API intake)."""

    sender_email: EmailStr
    sender_name: str | None = None
    subject: str
    body_text: str
    body_html: str | None = None
    source: Literal["api", "form", "email", "upload"] = "api"
    metadata: dict | None = None


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
    received_at: datetime
    processed_at: datetime | None


class MessageListResponse(BaseModel):
    """Paginated message list response."""

    items: list[MessageResponse]
    total: int
    page: int
    page_size: int
    pages: int


class AnalysisResponse(BaseModel):
    """Message analysis response."""

    message_id: UUID
    sentiment_score: float
    sentiment_label: str
    summary: str
    entities: list[dict]
    suggested_categories: list[dict]
    urgency_score: float


class MessageDetailResponse(MessageResponse):
    """Message detail with analysis."""

    analysis: AnalysisResponse | None = None


@router.post("", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    message: MessageCreate,
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """Submit a new message via API."""
    # TODO: Implement message creation and queue for processing
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Message creation not yet implemented",
    )


@router.get("", response_model=MessageListResponse)
async def list_messages(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source: str | None = None,
    sentiment: str | None = None,
    category_id: UUID | None = None,
    search: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    session: AsyncSession = Depends(get_session),
) -> MessageListResponse:
    """List messages with filters and pagination."""
    # TODO: Implement message listing with filters
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Message listing not yet implemented",
    )


@router.get("/{message_id}", response_model=MessageDetailResponse)
async def get_message(
    message_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> MessageDetailResponse:
    """Get message details with analysis."""
    # TODO: Implement message retrieval
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Message retrieval not yet implemented",
    )


@router.post("/email", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def receive_email_webhook(
    email_data: dict,
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """Receive email via webhook (from email service or Graph API)."""
    # TODO: Implement email webhook processing
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Email webhook not yet implemented",
    )
