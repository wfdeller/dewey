"""Outbound email marketing campaign endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select, func

from app.core.database import get_session
from app.api.v1.deps import PermissionChecker
from app.models.user import User, Permissions
from app.models.campaign import (
    Campaign,
    CampaignCreate,
    CampaignRead,
    CampaignUpdate,
    CampaignDetail,
    CampaignStatus,
    CampaignRecipient,
    CampaignRecipientRead,
    RecipientFilterPreview,
    CampaignAnalytics,
)
from app.models.contact import Contact
from app.models.email import EmailTemplate, EmailSuppression
from app.models.job import Job

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================


class CampaignListResponse(BaseModel):
    """Paginated campaign list response."""

    items: list[CampaignRead]
    total: int
    page: int
    page_size: int
    pages: int


class CampaignRecipientsResponse(BaseModel):
    """Paginated campaign recipients response."""

    items: list[CampaignRecipientRead]
    total: int
    page: int
    page_size: int
    pages: int


class CampaignStatsResponse(BaseModel):
    """Campaign statistics summary."""

    total_campaigns: int
    by_status: dict[str, int]
    total_sent: int
    total_opened: int
    total_clicked: int


class ScheduleRequest(BaseModel):
    """Request to schedule a campaign."""

    scheduled_at: datetime


class TestSendRequest(BaseModel):
    """Request to send test emails."""

    emails: list[EmailStr]


# =============================================================================
# Campaign CRUD Endpoints
# =============================================================================


@router.get("", response_model=CampaignListResponse)
async def list_campaigns(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: CampaignStatus | None = Query(None, alias="status"),
    search: str | None = Query(None, description="Search by name"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_READ)),
    session: AsyncSession = Depends(get_session),
) -> CampaignListResponse:
    """
    List outbound email campaigns with filters.

    Campaigns are outbound marketing emails sent to targeted contacts.
    """
    query = select(Campaign).where(Campaign.tenant_id == current_user.tenant_id)

    # Apply status filter
    if status_filter:
        query = query.where(Campaign.status == status_filter)

    # Apply search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.where(Campaign.name.ilike(search_pattern))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Apply sorting
    sort_column = getattr(Campaign, sort_by, Campaign.created_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await session.execute(query)
    campaigns = result.scalars().all()

    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return CampaignListResponse(
        items=[CampaignRead.model_validate(c) for c in campaigns],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("", response_model=CampaignRead, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    request: CampaignCreate,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> CampaignRead:
    """
    Create a new campaign draft.

    The campaign starts in 'draft' status and must be scheduled or started manually.
    """
    # Verify template exists and belongs to tenant
    template_result = await session.execute(
        select(EmailTemplate).where(
            EmailTemplate.id == request.template_id,
            EmailTemplate.tenant_id == current_user.tenant_id,
        )
    )
    if not template_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email template not found",
        )

    # Verify variant B template if provided
    if request.variant_b_template_id:
        variant_result = await session.execute(
            select(EmailTemplate).where(
                EmailTemplate.id == request.variant_b_template_id,
                EmailTemplate.tenant_id == current_user.tenant_id,
            )
        )
        if not variant_result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Variant B template not found",
            )

    campaign = Campaign(
        tenant_id=current_user.tenant_id,
        created_by_id=current_user.id,
        **request.model_dump(),
    )

    session.add(campaign)
    await session.commit()
    await session.refresh(campaign)

    return CampaignRead.model_validate(campaign)


@router.get("/{campaign_id}", response_model=CampaignDetail)
async def get_campaign(
    campaign_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_READ)),
    session: AsyncSession = Depends(get_session),
) -> CampaignDetail:
    """Get campaign details including configuration and stats."""
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
    Update a campaign.

    Only draft and scheduled campaigns can be modified.
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

    if campaign.status not in ("draft", "scheduled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot modify campaign in '{campaign.status}' status",
        )

    # Verify template if being updated
    if request.template_id:
        template_result = await session.execute(
            select(EmailTemplate).where(
                EmailTemplate.id == request.template_id,
                EmailTemplate.tenant_id == current_user.tenant_id,
            )
        )
        if not template_result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email template not found",
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
    Delete a campaign.

    Only draft campaigns can be deleted. Use cancel for active campaigns.
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

    if campaign.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft campaigns can be deleted. Use cancel for active campaigns.",
        )

    await session.delete(campaign)
    await session.commit()


# =============================================================================
# Campaign Lifecycle Endpoints
# =============================================================================


@router.post("/{campaign_id}/schedule", response_model=CampaignRead)
async def schedule_campaign(
    campaign_id: UUID,
    request: ScheduleRequest,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> CampaignRead:
    """
    Schedule a campaign for future sending.

    Requires recipients to be populated first.
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

    if campaign.status not in ("draft", "scheduled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot schedule campaign in '{campaign.status}' status",
        )

    if campaign.total_recipients == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Populate recipients before scheduling",
        )

    if request.scheduled_at <= datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scheduled time must be in the future",
        )

    campaign.scheduled_at = request.scheduled_at
    campaign.status = "scheduled"

    await session.commit()
    await session.refresh(campaign)

    return CampaignRead.model_validate(campaign)


@router.post("/{campaign_id}/start", response_model=CampaignRead)
async def start_campaign(
    campaign_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> CampaignRead:
    """
    Start sending campaign emails immediately.

    Requires recipients to be populated first.
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

    if campaign.status not in ("draft", "scheduled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start campaign in '{campaign.status}' status",
        )

    if campaign.total_recipients == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Populate recipients before starting",
        )

    campaign.status = "active"
    campaign.started_at = datetime.utcnow()

    # Create a job for tracking
    job = Job(
        tenant_id=current_user.tenant_id,
        job_type="campaign_send",
        status="pending",
        parameters={"campaign_id": str(campaign_id)},
        created_by_id=current_user.id,
    )
    session.add(job)
    await session.flush()

    campaign.job_id = job.id

    await session.commit()
    await session.refresh(campaign)

    # TODO: Enqueue ARQ task to send campaign emails
    # await arq_redis.enqueue_job("send_campaign_emails", job_id=job.id, ...)

    return CampaignRead.model_validate(campaign)


@router.post("/{campaign_id}/pause", response_model=CampaignRead)
async def pause_campaign(
    campaign_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> CampaignRead:
    """Pause an active campaign."""
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

    if campaign.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only active campaigns can be paused",
        )

    campaign.status = "paused"
    campaign.paused_at = datetime.utcnow()

    await session.commit()
    await session.refresh(campaign)

    return CampaignRead.model_validate(campaign)


@router.post("/{campaign_id}/resume", response_model=CampaignRead)
async def resume_campaign(
    campaign_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> CampaignRead:
    """Resume a paused campaign."""
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

    if campaign.status != "paused":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only paused campaigns can be resumed",
        )

    campaign.status = "active"
    campaign.paused_at = None

    await session.commit()
    await session.refresh(campaign)

    # TODO: Re-enqueue ARQ task to continue sending

    return CampaignRead.model_validate(campaign)


@router.post("/{campaign_id}/cancel", response_model=CampaignRead)
async def cancel_campaign(
    campaign_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> CampaignRead:
    """
    Cancel a campaign.

    This is irreversible. Emails already sent will not be recalled.
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

    if campaign.status in ("completed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Campaign is already {campaign.status}",
        )

    campaign.status = "cancelled"
    campaign.completed_at = datetime.utcnow()

    await session.commit()
    await session.refresh(campaign)

    return CampaignRead.model_validate(campaign)


# =============================================================================
# Recipient Management Endpoints
# =============================================================================


@router.get("/{campaign_id}/recipients", response_model=CampaignRecipientsResponse)
async def list_campaign_recipients(
    campaign_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_READ)),
    session: AsyncSession = Depends(get_session),
) -> CampaignRecipientsResponse:
    """Get campaign recipients with their delivery status."""
    # Verify campaign exists
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

    query = select(CampaignRecipient).where(CampaignRecipient.campaign_id == campaign_id)

    if status_filter:
        query = query.where(CampaignRecipient.status == status_filter)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(CampaignRecipient.created_at.desc()).offset(offset).limit(page_size)

    result = await session.execute(query)
    recipients = result.scalars().all()

    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return CampaignRecipientsResponse(
        items=[CampaignRecipientRead.model_validate(r) for r in recipients],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("/{campaign_id}/recipients/preview", response_model=RecipientFilterPreview)
async def preview_recipients(
    campaign_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_READ)),
    session: AsyncSession = Depends(get_session),
) -> RecipientFilterPreview:
    """
    Preview which contacts match the campaign's recipient filter.

    Returns count and sample contacts without creating recipient records.
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

    # Build contact query from filter
    query = await _build_recipient_query(
        session,
        current_user.tenant_id,
        campaign.recipient_filter,
    )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total_count = total_result.scalar() or 0

    # Get sample contacts
    sample_query = query.limit(10)
    sample_result = await session.execute(sample_query)
    sample_contacts = sample_result.scalars().all()

    return RecipientFilterPreview(
        total_count=total_count,
        sample_contacts=[
            {
                "id": str(c.id),
                "name": c.name,
                "email": c.email,
            }
            for c in sample_contacts
        ],
    )


@router.post("/{campaign_id}/recipients/populate", response_model=dict)
async def populate_recipients(
    campaign_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Create recipient records from the campaign's filter.

    This evaluates the filter and creates CampaignRecipient records
    for all matching contacts. Only draft/scheduled campaigns can be populated.
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

    if campaign.status not in ("draft", "scheduled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot populate recipients for campaign in '{campaign.status}' status",
        )

    # Clear existing recipients
    await session.execute(
        select(CampaignRecipient).where(CampaignRecipient.campaign_id == campaign_id)
    )
    existing = await session.execute(
        select(CampaignRecipient).where(CampaignRecipient.campaign_id == campaign_id)
    )
    for r in existing.scalars().all():
        await session.delete(r)

    # Build contact query from filter
    query = await _build_recipient_query(
        session,
        current_user.tenant_id,
        campaign.recipient_filter,
    )

    # Get all matching contacts
    contacts_result = await session.execute(query)
    contacts = contacts_result.scalars().all()

    # Determine A/B split if applicable
    variant_a_count = 0
    variant_b_count = 0
    is_ab_test = campaign.variant_b_template_id is not None

    created_count = 0
    for i, contact in enumerate(contacts):
        # Skip contacts without email
        if not contact.email:
            continue

        # Determine variant for A/B testing
        variant = None
        if is_ab_test:
            # Simple split based on index
            if (i % 100) < campaign.ab_test_split:
                variant = "a"
                variant_a_count += 1
            else:
                variant = "b"
                variant_b_count += 1

        recipient = CampaignRecipient(
            campaign_id=campaign_id,
            contact_id=contact.id,
            email=contact.email,
            variant=variant,
            status="pending",
        )
        session.add(recipient)
        created_count += 1

    # Update campaign stats
    campaign.total_recipients = created_count

    await session.commit()

    return {
        "total_recipients": created_count,
        "variant_a_count": variant_a_count if is_ab_test else None,
        "variant_b_count": variant_b_count if is_ab_test else None,
    }


# =============================================================================
# Test & Analytics Endpoints
# =============================================================================


@router.post("/{campaign_id}/test-send", response_model=dict)
async def send_test_email(
    campaign_id: UUID,
    request: TestSendRequest,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Send test emails to specified addresses.

    Test emails are not tracked in campaign statistics.
    """
    if len(request.emails) > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 5 test emails allowed",
        )

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

    # Verify template exists
    template_result = await session.execute(
        select(EmailTemplate).where(EmailTemplate.id == campaign.template_id)
    )
    template = template_result.scalars().first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign template not found",
        )

    # TODO: Send test emails via email service
    # For now, return success response

    return {
        "status": "sent",
        "emails": request.emails,
        "template_id": str(campaign.template_id),
    }


@router.get("/{campaign_id}/analytics", response_model=CampaignAnalytics)
async def get_campaign_analytics(
    campaign_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.ANALYTICS_READ)),
    session: AsyncSession = Depends(get_session),
) -> CampaignAnalytics:
    """Get detailed campaign analytics including rates and timeline."""
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

    # Calculate rates
    total = campaign.total_recipients or 1  # Avoid division by zero
    delivered = campaign.total_delivered or campaign.total_sent or 1

    analytics = CampaignAnalytics(
        campaign_id=campaign.id,
        status=campaign.status,
        total_recipients=campaign.total_recipients,
        total_sent=campaign.total_sent,
        total_delivered=campaign.total_delivered,
        total_opened=campaign.total_opened,
        total_clicked=campaign.total_clicked,
        total_bounced=campaign.total_bounced,
        total_unsubscribed=campaign.total_unsubscribed,
        total_failed=campaign.total_failed,
        delivery_rate=round((campaign.total_delivered / total) * 100, 2) if total > 0 else 0,
        open_rate=round((campaign.total_opened / delivered) * 100, 2) if delivered > 0 else 0,
        click_rate=round((campaign.total_clicked / delivered) * 100, 2) if delivered > 0 else 0,
        bounce_rate=round((campaign.total_bounced / total) * 100, 2) if total > 0 else 0,
        unsubscribe_rate=round((campaign.total_unsubscribed / delivered) * 100, 2)
        if delivered > 0
        else 0,
        unique_opens=campaign.unique_opens,
        unique_clicks=campaign.unique_clicks,
        unique_open_rate=round((campaign.unique_opens / delivered) * 100, 2)
        if delivered > 0
        else 0,
        unique_click_rate=round((campaign.unique_clicks / delivered) * 100, 2)
        if delivered > 0
        else 0,
        ab_test_results=await _get_ab_test_results(session, campaign)
        if campaign.variant_b_template_id
        else None,
    )

    return analytics


@router.get("/stats/summary", response_model=CampaignStatsResponse)
async def get_campaign_stats(
    current_user: User = Depends(PermissionChecker(Permissions.ANALYTICS_READ)),
    session: AsyncSession = Depends(get_session),
) -> CampaignStatsResponse:
    """Get summary statistics for all campaigns."""
    tenant_id = current_user.tenant_id

    # Count campaigns by status
    status_result = await session.execute(
        select(Campaign.status, func.count(Campaign.id))
        .where(Campaign.tenant_id == tenant_id)
        .group_by(Campaign.status)
    )
    status_counts = {row[0]: row[1] for row in status_result.all()}

    # Get aggregated stats
    stats_result = await session.execute(
        select(
            func.sum(Campaign.total_sent),
            func.sum(Campaign.total_opened),
            func.sum(Campaign.total_clicked),
        ).where(Campaign.tenant_id == tenant_id)
    )
    stats_row = stats_result.first()

    return CampaignStatsResponse(
        total_campaigns=sum(status_counts.values()),
        by_status=status_counts,
        total_sent=stats_row[0] or 0 if stats_row else 0,
        total_opened=stats_row[1] or 0 if stats_row else 0,
        total_clicked=stats_row[2] or 0 if stats_row else 0,
    )


# =============================================================================
# Helper Functions
# =============================================================================


async def _build_recipient_query(
    session: AsyncSession,
    tenant_id: UUID,
    recipient_filter: dict,
):
    """Build a SQLAlchemy query for contacts based on recipient filter."""
    query = select(Contact).where(
        Contact.tenant_id == tenant_id,
        Contact.email.isnot(None),
        Contact.email != "",
    )

    mode = recipient_filter.get("mode", "filter")

    if mode == "manual":
        # Manual contact selection
        manual_ids = recipient_filter.get("manual_contact_ids", [])
        if manual_ids:
            query = query.where(Contact.id.in_(manual_ids))
        else:
            # No contacts selected - return empty query
            query = query.where(Contact.id == None)  # noqa: E711
    else:
        # Filter-based selection
        # Filter by tags
        tags = recipient_filter.get("tags", [])
        if tags:
            tag_match = recipient_filter.get("tag_match", "any")
            if tag_match == "all":
                # Contact must have all tags
                for tag in tags:
                    query = query.where(Contact.tags.contains([tag]))
            else:
                # Contact must have any of the tags
                query = query.where(Contact.tags.overlap(tags))

        # Filter by state
        states = recipient_filter.get("states", [])
        if states:
            query = query.where(Contact.state.in_(states))

        # Filter by zip codes
        zip_codes = recipient_filter.get("zip_codes", [])
        if zip_codes:
            query = query.where(Contact.zip_code.in_(zip_codes))

        # TODO: Add category filter when MessageCategory join is implemented
        # TODO: Add custom field filters

    # Exclude suppressed emails (always)
    if recipient_filter.get("exclude_suppressed", True):
        # Subquery for suppressed emails
        suppressed_subquery = (
            select(EmailSuppression.email)
            .where(
                EmailSuppression.tenant_id == tenant_id,
                EmailSuppression.is_active == True,  # noqa: E712
            )
            .scalar_subquery()
        )
        query = query.where(Contact.email.notin_(suppressed_subquery))

    return query


async def _get_ab_test_results(session: AsyncSession, campaign: Campaign) -> dict | None:
    """Get A/B test comparison results."""
    if not campaign.variant_b_template_id:
        return None

    # Get variant A stats
    variant_a_result = await session.execute(
        select(
            func.count(CampaignRecipient.id).filter(CampaignRecipient.status != "pending"),
            func.count(CampaignRecipient.id).filter(CampaignRecipient.opened_at.isnot(None)),
            func.count(CampaignRecipient.id).filter(CampaignRecipient.clicked_at.isnot(None)),
        ).where(
            CampaignRecipient.campaign_id == campaign.id,
            CampaignRecipient.variant == "a",
        )
    )
    a_stats = variant_a_result.first()

    # Get variant B stats
    variant_b_result = await session.execute(
        select(
            func.count(CampaignRecipient.id).filter(CampaignRecipient.status != "pending"),
            func.count(CampaignRecipient.id).filter(CampaignRecipient.opened_at.isnot(None)),
            func.count(CampaignRecipient.id).filter(CampaignRecipient.clicked_at.isnot(None)),
        ).where(
            CampaignRecipient.campaign_id == campaign.id,
            CampaignRecipient.variant == "b",
        )
    )
    b_stats = variant_b_result.first()

    a_sent = a_stats[0] if a_stats else 0
    b_sent = b_stats[0] if b_stats else 0

    return {
        "variant_a": {
            "template_id": str(campaign.template_id),
            "sent": a_sent,
            "opened": a_stats[1] if a_stats else 0,
            "clicked": a_stats[2] if a_stats else 0,
            "open_rate": round((a_stats[1] / a_sent) * 100, 2) if a_sent > 0 else 0,
            "click_rate": round((a_stats[2] / a_sent) * 100, 2) if a_sent > 0 else 0,
        },
        "variant_b": {
            "template_id": str(campaign.variant_b_template_id),
            "sent": b_sent,
            "opened": b_stats[1] if b_stats else 0,
            "clicked": b_stats[2] if b_stats else 0,
            "open_rate": round((b_stats[1] / b_sent) * 100, 2) if b_sent > 0 else 0,
            "click_rate": round((b_stats[2] / b_sent) * 100, 2) if b_sent > 0 else 0,
        },
        "winner": campaign.ab_test_winning_variant,
        "winner_selected_at": campaign.ab_test_winner_selected_at.isoformat()
        if campaign.ab_test_winner_selected_at
        else None,
    }
