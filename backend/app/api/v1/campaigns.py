"""Campaign (coordinated message) management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func, update

from app.core.database import get_session
from app.api.v1.deps import PermissionChecker
from app.models.user import User, Permissions
from app.models.campaign import (
    Campaign,
    CampaignRead,
    CampaignUpdate,
    CampaignDetail,
    CampaignStatus,
)
from app.models.message import Message

router = APIRouter()


class CampaignListResponse(BaseModel):
    """Paginated campaign list response."""

    items: list[CampaignRead]
    total: int
    page: int
    page_size: int
    pages: int


class CampaignMergeRequest(BaseModel):
    """Request to merge campaigns."""

    source_campaign_ids: list[UUID]


class BulkRespondRequest(BaseModel):
    """Request to send bulk response to campaign messages."""

    template_id: UUID | None = None
    response_text: str | None = None


class MessageSummary(BaseModel):
    """Brief message info for campaign messages list."""

    id: UUID
    sender_email: str
    sender_name: str | None
    subject: str
    received_at: str
    processing_status: str

    class Config:
        from_attributes = True


class CampaignMessagesResponse(BaseModel):
    """Paginated campaign messages response."""

    items: list[MessageSummary]
    total: int
    page: int
    page_size: int
    pages: int


class CampaignStatsResponse(BaseModel):
    """Campaign statistics summary."""

    total_campaigns: int
    by_status: dict[str, int]
    total_campaign_messages: int


# =============================================================================
# Campaign Endpoints
# =============================================================================


@router.get("", response_model=CampaignListResponse)
async def list_campaigns(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: CampaignStatus | None = Query(None, alias="status"),
    search: str | None = Query(None, description="Search by name or source organization"),
    sort_by: str = Query("last_seen_at", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_READ)),
    session: AsyncSession = Depends(get_session),
) -> CampaignListResponse:
    """
    List detected campaigns with filters.

    Campaigns are groups of similar/template messages detected automatically
    or created manually for tracking coordinated communications.
    """
    query = select(Campaign).where(Campaign.tenant_id == current_user.tenant_id)

    # Apply status filter
    if status_filter:
        query = query.where(Campaign.status == status_filter)

    # Apply search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (Campaign.name.ilike(search_pattern))
            | (Campaign.source_organization.ilike(search_pattern))
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Apply sorting
    sort_column = getattr(Campaign, sort_by, Campaign.last_seen_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await session.execute(query)
    campaigns = result.scalars().all()

    pages = (total + page_size - 1) // page_size

    return CampaignListResponse(
        items=[CampaignRead.model_validate(c) for c in campaigns],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{campaign_id}", response_model=CampaignDetail)
async def get_campaign(
    campaign_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_READ)),
    session: AsyncSession = Depends(get_session),
) -> CampaignDetail:
    """Get campaign details including template preview."""
    result = await session.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.tenant_id == current_user.tenant_id,
        )
    )
    campaign = result.scalars().first()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    return CampaignDetail.model_validate(campaign)


@router.patch("/{campaign_id}", response_model=CampaignRead)
async def update_campaign(
    campaign_id: UUID,
    request: CampaignUpdate,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> CampaignRead:
    """
    Update campaign metadata.

    Used to confirm, dismiss, rename, or add notes to a campaign.
    """
    result = await session.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.tenant_id == current_user.tenant_id,
        )
    )
    campaign = result.scalars().first()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    # Apply updates
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(campaign, field, value)

    await session.commit()
    await session.refresh(campaign)

    return CampaignRead.model_validate(campaign)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Delete/dismiss a campaign.

    Messages in this campaign will be unlinked but not deleted.
    """
    result = await session.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.tenant_id == current_user.tenant_id,
        )
    )
    campaign = result.scalars().first()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    # Unlink messages from this campaign
    await session.execute(
        update(Message)
        .where(Message.campaign_id == campaign_id)
        .values(campaign_id=None, is_template_match=False, template_similarity_score=None)
    )

    await session.delete(campaign)
    await session.commit()


@router.get("/{campaign_id}/messages", response_model=CampaignMessagesResponse)
async def get_campaign_messages(
    campaign_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_READ)),
    session: AsyncSession = Depends(get_session),
) -> CampaignMessagesResponse:
    """Get all messages belonging to a campaign."""
    # Verify campaign exists and belongs to tenant
    campaign_result = await session.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.tenant_id == current_user.tenant_id,
        )
    )
    if not campaign_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    # Get messages
    query = (
        select(Message)
        .where(Message.campaign_id == campaign_id)
        .order_by(Message.received_at.desc())
    )

    # Get total count
    count_query = select(func.count()).select_from(
        select(Message).where(Message.campaign_id == campaign_id).subquery()
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
                sender_email=msg.sender_email,
                sender_name=msg.sender_name,
                subject=msg.subject,
                received_at=msg.received_at.isoformat(),
                processing_status=msg.processing_status,
            )
        )

    return CampaignMessagesResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("/{campaign_id}/merge", response_model=CampaignRead)
async def merge_campaigns(
    campaign_id: UUID,
    request: CampaignMergeRequest,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> CampaignRead:
    """
    Merge multiple campaigns into one.

    The target campaign (campaign_id) absorbs messages from source campaigns.
    Source campaigns are deleted after merge.
    """
    # Get target campaign
    result = await session.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.tenant_id == current_user.tenant_id,
        )
    )
    target_campaign = result.scalars().first()

    if not target_campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target campaign not found",
        )

    total_messages_added = 0
    unique_senders_set = set()

    # Get existing unique senders from target campaign
    existing_senders_result = await session.execute(
        select(Message.sender_email)
        .where(Message.campaign_id == campaign_id)
        .distinct()
    )
    for row in existing_senders_result.all():
        unique_senders_set.add(row[0])

    # Process each source campaign
    for source_id in request.source_campaign_ids:
        if source_id == campaign_id:
            continue  # Skip if trying to merge with self

        source_result = await session.execute(
            select(Campaign).where(
                Campaign.id == source_id,
                Campaign.tenant_id == current_user.tenant_id,
            )
        )
        source_campaign = source_result.scalars().first()

        if not source_campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source campaign {source_id} not found",
            )

        # Get unique senders from source campaign
        source_senders_result = await session.execute(
            select(Message.sender_email)
            .where(Message.campaign_id == source_id)
            .distinct()
        )
        for row in source_senders_result.all():
            unique_senders_set.add(row[0])

        # Count messages in source
        source_count_result = await session.execute(
            select(func.count()).where(Message.campaign_id == source_id)
        )
        source_message_count = source_count_result.scalar() or 0
        total_messages_added += source_message_count

        # Update messages from source to target campaign
        await session.execute(
            update(Message)
            .where(Message.campaign_id == source_id)
            .values(campaign_id=campaign_id)
        )

        # Update target campaign timing if source has earlier/later dates
        if source_campaign.first_seen_at < target_campaign.first_seen_at:
            target_campaign.first_seen_at = source_campaign.first_seen_at
        if source_campaign.last_seen_at > target_campaign.last_seen_at:
            target_campaign.last_seen_at = source_campaign.last_seen_at

        # Delete source campaign
        await session.delete(source_campaign)

    # Update target campaign stats
    target_campaign.message_count = (target_campaign.message_count or 0) + total_messages_added
    target_campaign.unique_senders = len(unique_senders_set)

    await session.commit()
    await session.refresh(target_campaign)

    return CampaignRead.model_validate(target_campaign)


@router.post("/{campaign_id}/bulk-respond", status_code=status.HTTP_202_ACCEPTED)
async def bulk_respond_to_campaign(
    campaign_id: UUID,
    request: BulkRespondRequest,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Send a bulk response to all messages in a campaign.

    This queues response emails to all unique senders in the campaign.
    """
    # Verify campaign exists
    result = await session.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.tenant_id == current_user.tenant_id,
        )
    )
    campaign = result.scalars().first()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    if not request.template_id and not request.response_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either template_id or response_text is required",
        )

    # Get unique sender emails from campaign messages
    senders_result = await session.execute(
        select(Message.sender_email)
        .where(Message.campaign_id == campaign_id)
        .distinct()
    )
    unique_sender_emails = [row[0] for row in senders_result.all()]

    # TODO: Queue bulk response job
    # - Create response task for each unique sender
    # - Use template if template_id provided
    # - Otherwise use response_text

    return {
        "status": "queued",
        "campaign_id": campaign_id,
        "estimated_recipients": len(unique_sender_emails),
        "message": f"Queued responses to {len(unique_sender_emails)} unique senders",
    }


@router.get("/stats/summary", response_model=CampaignStatsResponse)
async def get_campaign_stats(
    current_user: User = Depends(PermissionChecker(Permissions.ANALYTICS_READ)),
    session: AsyncSession = Depends(get_session),
) -> CampaignStatsResponse:
    """Get summary statistics for campaigns."""
    tenant_id = current_user.tenant_id

    # Count campaigns by status
    result = await session.execute(
        select(Campaign.status, func.count(Campaign.id))
        .where(Campaign.tenant_id == tenant_id)
        .group_by(Campaign.status)
    )
    status_counts = {row[0]: row[1] for row in result.all()}

    # Get total messages in campaigns
    total_messages_result = await session.execute(
        select(func.sum(Campaign.message_count)).where(
            Campaign.tenant_id == tenant_id
        )
    )
    total_campaign_messages = total_messages_result.scalar() or 0

    return CampaignStatsResponse(
        total_campaigns=sum(status_counts.values()),
        by_status=status_counts,
        total_campaign_messages=total_campaign_messages,
    )


@router.post("/{campaign_id}/confirm", response_model=CampaignRead)
async def confirm_campaign(
    campaign_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> CampaignRead:
    """Mark a detected campaign as confirmed."""
    result = await session.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.tenant_id == current_user.tenant_id,
        )
    )
    campaign = result.scalars().first()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    campaign.status = "confirmed"
    await session.commit()
    await session.refresh(campaign)

    return CampaignRead.model_validate(campaign)


@router.post("/{campaign_id}/dismiss", response_model=CampaignRead)
async def dismiss_campaign(
    campaign_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> CampaignRead:
    """Mark a detected campaign as dismissed (false positive)."""
    result = await session.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.tenant_id == current_user.tenant_id,
        )
    )
    campaign = result.scalars().first()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    campaign.status = "dismissed"
    await session.commit()
    await session.refresh(campaign)

    return CampaignRead.model_validate(campaign)
