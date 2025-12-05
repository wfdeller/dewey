"""Analytics and reporting endpoints."""

from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func

from app.core.database import get_session
from app.api.v1.deps import AuthContext, PermissionChecker, ScopeChecker
from app.models.user import User, Permissions
from app.models.message import Message
from app.models.analysis import Analysis
from app.models.contact import Contact
from app.models.category import Category, MessageCategory
from app.models.campaign import Campaign

router = APIRouter()


class DateRangeParams(BaseModel):
    """Common date range parameters."""

    start_date: datetime
    end_date: datetime


class SentimentTrendPoint(BaseModel):
    """Single point in sentiment trend."""

    date: str
    avg_sentiment: float
    message_count: int


class SentimentTrendResponse(BaseModel):
    """Sentiment trend over time."""

    data: list[SentimentTrendPoint]
    period: str
    total_messages: int
    avg_sentiment: float


class VolumePoint(BaseModel):
    """Single point in volume trend."""

    date: str
    count: int
    by_source: dict[str, int] | None = None


class VolumeResponse(BaseModel):
    """Message volume over time."""

    data: list[VolumePoint]
    period: str
    total: int


class CategoryBreakdown(BaseModel):
    """Category statistics."""

    category_id: UUID
    category_name: str
    count: int
    percentage: float
    avg_sentiment: float | None


class CategoryBreakdownResponse(BaseModel):
    """Category distribution."""

    data: list[CategoryBreakdown]
    total_categorized: int
    total_uncategorized: int


class TopContact(BaseModel):
    """Top contact entry."""

    contact_id: UUID
    email: str
    name: str | None
    message_count: int
    avg_sentiment: float | None
    last_contact_at: datetime | None


class TopContactsResponse(BaseModel):
    """Top contacts by volume or sentiment."""

    data: list[TopContact]
    sort_by: str


class DashboardSummary(BaseModel):
    """Dashboard summary statistics."""

    total_messages: int
    messages_today: int
    messages_this_week: int
    avg_sentiment: float | None
    sentiment_distribution: dict[str, int]
    top_categories: list[dict]
    active_campaigns: int
    pending_messages: int


class ExportRequest(BaseModel):
    """Request for data export."""

    dataset: str  # messages, contacts, analytics
    format: str = "csv"  # csv, json
    filters: dict | None = None
    columns: list[str] | None = None


# =============================================================================
# Analytics Endpoints
# =============================================================================


@router.get("/dashboard", response_model=DashboardSummary)
async def get_dashboard_summary(
    current_user: User = Depends(PermissionChecker(Permissions.ANALYTICS_READ)),
    session: AsyncSession = Depends(get_session),
) -> DashboardSummary:
    """Get dashboard summary statistics."""
    tenant_id = current_user.tenant_id
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    # Total messages
    total_result = await session.execute(
        select(func.count()).where(Message.tenant_id == tenant_id)
    )
    total_messages = total_result.scalar() or 0

    # Messages today
    today_result = await session.execute(
        select(func.count()).where(
            Message.tenant_id == tenant_id,
            Message.received_at >= today_start,
        )
    )
    messages_today = today_result.scalar() or 0

    # Messages this week
    week_result = await session.execute(
        select(func.count()).where(
            Message.tenant_id == tenant_id,
            Message.received_at >= week_start,
        )
    )
    messages_this_week = week_result.scalar() or 0

    # Average sentiment (from Analysis)
    # TODO: Join with Analysis table for sentiment

    # Sentiment distribution
    # TODO: Query Analysis table grouped by sentiment_label

    # Top categories
    # TODO: Query MessageCategory grouped by category_id

    # Active campaigns
    campaigns_result = await session.execute(
        select(func.count()).where(
            Campaign.tenant_id == tenant_id,
            Campaign.status == "detected",
        )
    )
    active_campaigns = campaigns_result.scalar() or 0

    # Pending messages
    pending_result = await session.execute(
        select(func.count()).where(
            Message.tenant_id == tenant_id,
            Message.processing_status == "pending",
        )
    )
    pending_messages = pending_result.scalar() or 0

    return DashboardSummary(
        total_messages=total_messages,
        messages_today=messages_today,
        messages_this_week=messages_this_week,
        avg_sentiment=None,  # TODO
        sentiment_distribution={},  # TODO
        top_categories=[],  # TODO
        active_campaigns=active_campaigns,
        pending_messages=pending_messages,
    )


@router.get("/sentiment", response_model=SentimentTrendResponse)
async def get_sentiment_trend(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    granularity: str = Query("day", pattern="^(hour|day|week|month)$"),
    category_id: UUID | None = None,
    current_user: User = Depends(PermissionChecker(Permissions.ANALYTICS_READ)),
    session: AsyncSession = Depends(get_session),
) -> SentimentTrendResponse:
    """
    Get sentiment trend over time.

    Returns average sentiment score and message count per time period.
    """
    # TODO: Implement sentiment trend query
    # - Join Message with Analysis
    # - Group by date truncated to granularity
    # - Filter by date range and optional category
    # - Calculate avg sentiment and count per period

    return SentimentTrendResponse(
        data=[],  # TODO: Populate
        period=granularity,
        total_messages=0,
        avg_sentiment=0.0,
    )


@router.get("/volume", response_model=VolumeResponse)
async def get_message_volume(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    granularity: str = Query("day", pattern="^(hour|day|week|month)$"),
    by_source: bool = Query(False, description="Break down by message source"),
    current_user: User = Depends(PermissionChecker(Permissions.ANALYTICS_READ)),
    session: AsyncSession = Depends(get_session),
) -> VolumeResponse:
    """
    Get message volume over time.

    Returns message count per time period, optionally broken down by source.
    """
    # TODO: Implement volume query
    # - Group by date truncated to granularity
    # - Optionally group by source
    # - Filter by date range

    return VolumeResponse(
        data=[],  # TODO: Populate
        period=granularity,
        total=0,
    )


@router.get("/categories", response_model=CategoryBreakdownResponse)
async def get_category_breakdown(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    current_user: User = Depends(PermissionChecker(Permissions.ANALYTICS_READ)),
    session: AsyncSession = Depends(get_session),
) -> CategoryBreakdownResponse:
    """
    Get message distribution across categories.

    Returns count and percentage for each category.
    """
    tenant_id = current_user.tenant_id

    # Get categories with message counts
    # TODO: Join MessageCategory with Category and Message
    # TODO: Filter by date range if provided
    # TODO: Calculate percentages

    # Get total categorized
    categorized_result = await session.execute(
        select(func.count(func.distinct(MessageCategory.message_id)))
        # TODO: Filter by tenant through Message join
    )
    total_categorized = categorized_result.scalar() or 0

    # Get total uncategorized
    # TODO: Count messages without any category assignment

    return CategoryBreakdownResponse(
        data=[],  # TODO: Populate
        total_categorized=total_categorized,
        total_uncategorized=0,  # TODO
    )


@router.get("/contacts/top", response_model=TopContactsResponse)
async def get_top_contacts(
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = Query("message_count", pattern="^(message_count|avg_sentiment|last_contact)$"),
    sentiment_filter: str | None = Query(None, pattern="^(positive|neutral|negative)$"),
    current_user: User = Depends(PermissionChecker(Permissions.ANALYTICS_READ)),
    session: AsyncSession = Depends(get_session),
) -> TopContactsResponse:
    """
    Get top contacts by volume or sentiment.

    Useful for identifying most active or most positive/negative constituents.
    """
    tenant_id = current_user.tenant_id

    query = select(Contact).where(Contact.tenant_id == tenant_id)

    # Apply sorting
    if sort_by == "message_count":
        query = query.order_by(Contact.message_count.desc())
    elif sort_by == "avg_sentiment":
        query = query.order_by(Contact.avg_sentiment.desc())
    elif sort_by == "last_contact":
        query = query.order_by(Contact.last_contact_at.desc())

    # TODO: Filter by sentiment if specified

    query = query.limit(limit)

    result = await session.execute(query)
    contacts = result.scalars().all()

    return TopContactsResponse(
        data=[
            TopContact(
                contact_id=c.id,
                email=c.email,
                name=c.name,
                message_count=c.message_count,
                avg_sentiment=c.avg_sentiment,
                last_contact_at=c.last_contact_at,
            )
            for c in contacts
        ],
        sort_by=sort_by,
    )


@router.get("/campaigns/comparison")
async def get_campaign_comparison(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    current_user: User = Depends(PermissionChecker(Permissions.ANALYTICS_READ)),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Compare campaign messages vs organic messages.

    Returns counts and sentiment comparison between coordinated and organic messages.
    """
    tenant_id = current_user.tenant_id

    # Count campaign messages
    campaign_result = await session.execute(
        select(func.count()).where(
            Message.tenant_id == tenant_id,
            Message.is_template_match == True,
        )
    )
    campaign_count = campaign_result.scalar() or 0

    # Count organic messages
    organic_result = await session.execute(
        select(func.count()).where(
            Message.tenant_id == tenant_id,
            Message.is_template_match == False,
        )
    )
    organic_count = organic_result.scalar() or 0

    # TODO: Calculate avg sentiment for each group

    return {
        "campaign_messages": {
            "count": campaign_count,
            "avg_sentiment": None,  # TODO
        },
        "organic_messages": {
            "count": organic_count,
            "avg_sentiment": None,  # TODO
        },
        "campaign_percentage": (
            round(campaign_count / (campaign_count + organic_count) * 100, 1)
            if (campaign_count + organic_count) > 0
            else 0
        ),
    }


@router.get("/custom-fields/{field_id}")
async def get_custom_field_analytics(
    field_id: UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    current_user: User = Depends(PermissionChecker(Permissions.ANALYTICS_READ)),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Get analytics breakdown by custom field values.

    E.g., sentiment distribution by party affiliation or district.
    """
    # TODO: Verify field belongs to tenant
    # TODO: Query contacts grouped by field value
    # TODO: Calculate message counts and avg sentiment per value

    return {
        "field_id": field_id,
        "breakdown": [],  # TODO: Populate
    }


@router.get("/response-times")
async def get_response_time_metrics(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    current_user: User = Depends(PermissionChecker(Permissions.ANALYTICS_READ)),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Get message processing time metrics.

    Shows how quickly messages are being processed and analyzed.
    """
    # TODO: Calculate processing times from received_at to processed_at

    return {
        "avg_processing_time_seconds": None,  # TODO
        "median_processing_time_seconds": None,  # TODO
        "p95_processing_time_seconds": None,  # TODO
        "messages_processed": 0,  # TODO
        "messages_pending": 0,  # TODO
    }


# =============================================================================
# Export Endpoints
# =============================================================================


@router.post("/export")
async def export_data(
    request: ExportRequest,
    current_user: User = Depends(PermissionChecker(Permissions.ANALYTICS_EXPORT)),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Request a data export.

    Returns a job ID to track export progress. Large exports are processed async.
    """
    # TODO: Validate dataset and columns
    # TODO: Queue export job
    # TODO: Return job ID

    return {
        "job_id": "placeholder",
        "status": "queued",
        "dataset": request.dataset,
        "format": request.format,
    }


@router.get("/export/{job_id}/status")
async def get_export_status(
    job_id: str,
    current_user: User = Depends(PermissionChecker(Permissions.ANALYTICS_EXPORT)),
) -> dict:
    """Get status of an export job."""
    # TODO: Look up job status

    return {
        "job_id": job_id,
        "status": "completed",  # TODO
        "download_url": None,  # TODO
        "expires_at": None,  # TODO
    }


@router.get("/export/{job_id}/download")
async def download_export(
    job_id: str,
    current_user: User = Depends(PermissionChecker(Permissions.ANALYTICS_EXPORT)),
) -> StreamingResponse:
    """Download a completed export."""
    # TODO: Look up job, verify completed, stream file

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Export download not yet implemented",
    )


# =============================================================================
# API Key Analytics (for external tools like Power BI)
# =============================================================================


@router.get("/datasets")
async def list_available_datasets(
    auth: AuthContext = Depends(ScopeChecker("analytics:read")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    List available analytics datasets.

    Used by external tools to discover available data.
    """
    return {
        "datasets": [
            {
                "name": "messages_summary",
                "description": "Core message data with sentiment analysis",
                "endpoint": "/api/v1/analytics/datasets/messages_summary",
            },
            {
                "name": "sentiment_trends",
                "description": "Daily sentiment aggregates",
                "endpoint": "/api/v1/analytics/datasets/sentiment_trends",
            },
            {
                "name": "category_breakdown",
                "description": "Messages by category",
                "endpoint": "/api/v1/analytics/datasets/category_breakdown",
            },
            {
                "name": "contact_analytics",
                "description": "Contact engagement metrics",
                "endpoint": "/api/v1/analytics/datasets/contact_analytics",
            },
            {
                "name": "campaign_summary",
                "description": "Coordinated campaign statistics",
                "endpoint": "/api/v1/analytics/datasets/campaign_summary",
            },
        ]
    }


@router.get("/datasets/{dataset_name}")
async def query_dataset(
    dataset_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    auth: AuthContext = Depends(ScopeChecker("analytics:read")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Query a specific analytics dataset.

    Supports pagination for large datasets. Used by Power BI and similar tools.
    """
    valid_datasets = [
        "messages_summary",
        "sentiment_trends",
        "category_breakdown",
        "contact_analytics",
        "campaign_summary",
    ]

    if dataset_name not in valid_datasets:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset not found. Valid datasets: {', '.join(valid_datasets)}",
        )

    # TODO: Implement dataset queries
    # Each dataset maps to a PostgreSQL view or query

    return {
        "dataset": dataset_name,
        "data": [],  # TODO: Populate
        "page": page,
        "page_size": page_size,
        "total": 0,  # TODO
    }
