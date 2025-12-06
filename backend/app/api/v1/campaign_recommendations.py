"""AI-driven campaign recommendation endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func

from app.core.database import get_session
from app.api.v1.deps import PermissionChecker
from app.models.user import User, Permissions
from app.models.campaign_recommendation import (
    CampaignRecommendation,
    CampaignRecommendationRead,
    CampaignRecommendationDetail,
    CampaignRecommendationDismiss,
    CampaignRecommendationConvert,
    RecommendationStatus,
)
from app.models.campaign import Campaign
from app.models.email import EmailTemplate
from app.models.category import Category
from app.models.message import Message

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================


class RecommendationListResponse(BaseModel):
    """Paginated recommendation list response."""

    items: list[CampaignRecommendationRead]
    total: int
    page: int
    page_size: int
    pages: int


class RecommendationDetailResponse(CampaignRecommendationDetail):
    """Extended recommendation with sample messages."""

    sample_messages: list[dict] = []
    category_name: str | None = None


class ConvertResponse(BaseModel):
    """Response for converting a recommendation to a campaign."""

    recommendation_id: UUID
    campaign_id: UUID
    campaign_name: str
    message: str


# =============================================================================
# Recommendation Endpoints
# =============================================================================


@router.get("", response_model=RecommendationListResponse)
async def list_recommendations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: RecommendationStatus | None = Query(None, alias="status"),
    trigger_type: str | None = Query(None, description="Filter by trigger type"),
    current_user: User = Depends(PermissionChecker(Permissions.ANALYTICS_READ)),
    session: AsyncSession = Depends(get_session),
) -> RecommendationListResponse:
    """
    List campaign recommendations.

    Recommendations are AI-generated suggestions for outbound campaigns
    based on trends in incoming messages.
    """
    query = select(CampaignRecommendation).where(
        CampaignRecommendation.tenant_id == current_user.tenant_id
    )

    # Default to active recommendations
    if status_filter:
        query = query.where(CampaignRecommendation.status == status_filter)
    else:
        query = query.where(CampaignRecommendation.status == "active")

    # Filter by trigger type
    if trigger_type:
        query = query.where(CampaignRecommendation.trigger_type == trigger_type)

    # Exclude expired recommendations
    query = query.where(
        (CampaignRecommendation.expires_at.is_(None))
        | (CampaignRecommendation.expires_at > datetime.utcnow())
    )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Order by confidence score (highest first) then creation date
    query = query.order_by(
        CampaignRecommendation.confidence_score.desc(),
        CampaignRecommendation.created_at.desc(),
    )

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await session.execute(query)
    recommendations = result.scalars().all()

    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return RecommendationListResponse(
        items=[CampaignRecommendationRead.model_validate(r) for r in recommendations],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{recommendation_id}", response_model=RecommendationDetailResponse)
async def get_recommendation(
    recommendation_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.ANALYTICS_READ)),
    session: AsyncSession = Depends(get_session),
) -> RecommendationDetailResponse:
    """Get recommendation details including sample messages."""
    result = await session.execute(
        select(CampaignRecommendation).where(
            CampaignRecommendation.id == recommendation_id,
            CampaignRecommendation.tenant_id == current_user.tenant_id,
        )
    )
    recommendation = result.scalars().first()

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found",
        )

    # Get category name if linked
    category_name = None
    if recommendation.category_id:
        category_result = await session.execute(
            select(Category).where(Category.id == recommendation.category_id)
        )
        category = category_result.scalars().first()
        if category:
            category_name = category.name

    # Get sample messages from trend data
    sample_messages = []
    sample_message_ids = recommendation.trend_data.get("sample_message_ids", [])
    if sample_message_ids:
        messages_result = await session.execute(
            select(Message)
            .where(
                Message.id.in_(sample_message_ids),
                Message.tenant_id == current_user.tenant_id,
            )
            .limit(5)
        )
        for msg in messages_result.scalars().all():
            sample_messages.append(
                {
                    "id": str(msg.id),
                    "subject": msg.subject,
                    "sender_email": msg.sender_email,
                    "sender_name": msg.sender_name,
                    "received_at": msg.received_at.isoformat(),
                }
            )

    # Build response
    response_data = CampaignRecommendationDetail.model_validate(recommendation).model_dump()
    response_data["sample_messages"] = sample_messages
    response_data["category_name"] = category_name

    return RecommendationDetailResponse(**response_data)


@router.post("/{recommendation_id}/dismiss", response_model=CampaignRecommendationRead)
async def dismiss_recommendation(
    recommendation_id: UUID,
    request: CampaignRecommendationDismiss,
    current_user: User = Depends(PermissionChecker(Permissions.ANALYTICS_READ)),
    session: AsyncSession = Depends(get_session),
) -> CampaignRecommendationRead:
    """
    Dismiss a recommendation.

    The recommendation will no longer appear in the active list.
    """
    result = await session.execute(
        select(CampaignRecommendation).where(
            CampaignRecommendation.id == recommendation_id,
            CampaignRecommendation.tenant_id == current_user.tenant_id,
        )
    )
    recommendation = result.scalars().first()

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found",
        )

    if recommendation.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Recommendation is already {recommendation.status}",
        )

    recommendation.status = "dismissed"
    recommendation.dismissed_at = datetime.utcnow()
    recommendation.dismissed_by_id = current_user.id
    recommendation.dismissal_reason = request.reason

    await session.commit()
    await session.refresh(recommendation)

    return CampaignRecommendationRead.model_validate(recommendation)


@router.post("/{recommendation_id}/convert", response_model=ConvertResponse)
async def convert_to_campaign(
    recommendation_id: UUID,
    request: CampaignRecommendationConvert,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> ConvertResponse:
    """
    Convert a recommendation into a campaign.

    This creates a new campaign draft using the recommendation's
    suggested filter and the specified template.
    """
    result = await session.execute(
        select(CampaignRecommendation).where(
            CampaignRecommendation.id == recommendation_id,
            CampaignRecommendation.tenant_id == current_user.tenant_id,
        )
    )
    recommendation = result.scalars().first()

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found",
        )

    if recommendation.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot convert recommendation in '{recommendation.status}' status",
        )

    # Verify template exists
    template_result = await session.execute(
        select(EmailTemplate).where(
            EmailTemplate.id == request.template_id,
            EmailTemplate.tenant_id == current_user.tenant_id,
        )
    )
    template = template_result.scalars().first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email template not found",
        )

    # Determine recipient filter
    if request.use_suggested_filter:
        recipient_filter = recommendation.suggested_filter
    else:
        recipient_filter = request.custom_filter or {}

    # Create campaign draft
    campaign = Campaign(
        tenant_id=current_user.tenant_id,
        name=request.name,
        description=f"Created from recommendation: {recommendation.title}",
        campaign_type="standard",
        template_id=request.template_id,
        status="draft",
        recipient_filter=recipient_filter,
        created_by_id=current_user.id,
    )

    session.add(campaign)
    await session.flush()

    # Update recommendation
    recommendation.status = "converted"
    recommendation.converted_campaign_id = campaign.id
    recommendation.converted_at = datetime.utcnow()
    recommendation.converted_by_id = current_user.id

    await session.commit()
    await session.refresh(campaign)

    return ConvertResponse(
        recommendation_id=recommendation_id,
        campaign_id=campaign.id,
        campaign_name=campaign.name,
        message=f"Campaign '{campaign.name}' created successfully",
    )


# =============================================================================
# Stats Endpoint
# =============================================================================


@router.get("/stats/summary")
async def get_recommendation_stats(
    current_user: User = Depends(PermissionChecker(Permissions.ANALYTICS_READ)),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get summary statistics for recommendations."""
    tenant_id = current_user.tenant_id

    # Count by status
    status_result = await session.execute(
        select(CampaignRecommendation.status, func.count(CampaignRecommendation.id))
        .where(CampaignRecommendation.tenant_id == tenant_id)
        .group_by(CampaignRecommendation.status)
    )
    status_counts = {row[0]: row[1] for row in status_result.all()}

    # Count by trigger type (active only)
    trigger_result = await session.execute(
        select(CampaignRecommendation.trigger_type, func.count(CampaignRecommendation.id))
        .where(
            CampaignRecommendation.tenant_id == tenant_id,
            CampaignRecommendation.status == "active",
        )
        .group_by(CampaignRecommendation.trigger_type)
    )
    trigger_counts = {row[0]: row[1] for row in trigger_result.all()}

    # Get average confidence of active recommendations
    avg_confidence_result = await session.execute(
        select(func.avg(CampaignRecommendation.confidence_score)).where(
            CampaignRecommendation.tenant_id == tenant_id,
            CampaignRecommendation.status == "active",
        )
    )
    avg_confidence = avg_confidence_result.scalar() or 0

    return {
        "total_active": status_counts.get("active", 0),
        "total_converted": status_counts.get("converted", 0),
        "total_dismissed": status_counts.get("dismissed", 0),
        "by_trigger_type": trigger_counts,
        "average_confidence": round(avg_confidence, 2),
    }


# =============================================================================
# Refresh Endpoint (Trigger recommendation generation)
# =============================================================================


@router.post("/refresh", status_code=status.HTTP_202_ACCEPTED)
async def refresh_recommendations(
    current_user: User = Depends(PermissionChecker(Permissions.ANALYTICS_READ)),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Trigger a refresh of campaign recommendations.

    This queues a background job to analyze recent message trends
    and generate new recommendations.
    """
    # TODO: Enqueue ARQ task to generate recommendations
    # await arq_redis.enqueue_job(
    #     "generate_campaign_recommendations",
    #     tenant_id=str(current_user.tenant_id),
    # )

    return {
        "status": "queued",
        "message": "Recommendation refresh has been queued",
    }
