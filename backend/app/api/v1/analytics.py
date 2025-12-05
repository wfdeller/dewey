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

    # Average sentiment
    avg_sentiment_result = await session.execute(
        select(func.avg(Analysis.sentiment_score))
        .join(Message, Message.id == Analysis.message_id)
        .where(Message.tenant_id == tenant_id)
    )
    avg_sentiment = avg_sentiment_result.scalar()

    # Sentiment distribution
    sentiment_dist_result = await session.execute(
        select(Analysis.sentiment_label, func.count())
        .join(Message, Message.id == Analysis.message_id)
        .where(Message.tenant_id == tenant_id)
        .group_by(Analysis.sentiment_label)
    )
    sentiment_distribution = {row[0]: row[1] for row in sentiment_dist_result.all()}

    # Top categories (top 5)
    top_categories_result = await session.execute(
        select(Category.id, Category.name, Category.color, func.count(MessageCategory.message_id))
        .join(MessageCategory, MessageCategory.category_id == Category.id)
        .join(Message, Message.id == MessageCategory.message_id)
        .where(Message.tenant_id == tenant_id)
        .group_by(Category.id, Category.name, Category.color)
        .order_by(func.count(MessageCategory.message_id).desc())
        .limit(5)
    )
    top_categories = [
        {"id": str(row[0]), "name": row[1], "color": row[2], "count": row[3]}
        for row in top_categories_result.all()
    ]

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
        avg_sentiment=float(avg_sentiment) if avg_sentiment else None,
        sentiment_distribution=sentiment_distribution,
        top_categories=top_categories,
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
    tenant_id = current_user.tenant_id

    # Build query
    query = (
        select(
            func.date_trunc(granularity, Message.received_at).label("date"),
            func.avg(Analysis.sentiment_score).label("avg_sentiment"),
            func.count(Message.id).label("message_count"),
        )
        .join(Analysis, Analysis.message_id == Message.id)
        .where(
            Message.tenant_id == tenant_id,
            Message.received_at >= start_date,
            Message.received_at <= end_date,
        )
        .group_by(func.date_trunc(granularity, Message.received_at))
        .order_by(func.date_trunc(granularity, Message.received_at))
    )

    # Filter by category if specified
    if category_id:
        query = query.join(MessageCategory, MessageCategory.message_id == Message.id).where(
            MessageCategory.category_id == category_id
        )

    result = await session.execute(query)
    rows = result.all()

    data = []
    total_messages = 0
    sentiment_sum = 0

    for row in rows:
        point = SentimentTrendPoint(
            date=row.date.strftime("%Y-%m-%d") if row.date else "",
            avg_sentiment=float(row.avg_sentiment) if row.avg_sentiment else 0,
            message_count=row.message_count or 0,
        )
        data.append(point)
        total_messages += row.message_count or 0
        if row.avg_sentiment:
            sentiment_sum += row.avg_sentiment * row.message_count

    overall_avg = sentiment_sum / total_messages if total_messages > 0 else 0

    return SentimentTrendResponse(
        data=data,
        period=granularity,
        total_messages=total_messages,
        avg_sentiment=overall_avg,
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
    tenant_id = current_user.tenant_id

    if by_source:
        # Query with source breakdown
        query = (
            select(
                func.date_trunc(granularity, Message.received_at).label("date"),
                Message.source,
                func.count(Message.id).label("count"),
            )
            .where(
                Message.tenant_id == tenant_id,
                Message.received_at >= start_date,
                Message.received_at <= end_date,
            )
            .group_by(func.date_trunc(granularity, Message.received_at), Message.source)
            .order_by(func.date_trunc(granularity, Message.received_at))
        )

        result = await session.execute(query)
        rows = result.all()

        # Aggregate by date
        date_data = {}
        total = 0
        for row in rows:
            date_str = row.date.strftime("%Y-%m-%d") if row.date else ""
            if date_str not in date_data:
                date_data[date_str] = {"count": 0, "by_source": {}}
            date_data[date_str]["count"] += row.count or 0
            date_data[date_str]["by_source"][row.source] = row.count or 0
            total += row.count or 0

        data = [
            VolumePoint(date=date, count=info["count"], by_source=info["by_source"])
            for date, info in sorted(date_data.items())
        ]
    else:
        # Simple query without source breakdown
        query = (
            select(
                func.date_trunc(granularity, Message.received_at).label("date"),
                func.count(Message.id).label("count"),
            )
            .where(
                Message.tenant_id == tenant_id,
                Message.received_at >= start_date,
                Message.received_at <= end_date,
            )
            .group_by(func.date_trunc(granularity, Message.received_at))
            .order_by(func.date_trunc(granularity, Message.received_at))
        )

        result = await session.execute(query)
        rows = result.all()

        data = []
        total = 0
        for row in rows:
            point = VolumePoint(
                date=row.date.strftime("%Y-%m-%d") if row.date else "",
                count=row.count or 0,
            )
            data.append(point)
            total += row.count or 0

    return VolumeResponse(
        data=data,
        period=granularity,
        total=total,
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

    # Build base query for category counts
    query = (
        select(
            Category.id,
            Category.name,
            func.count(MessageCategory.message_id).label("count"),
            func.avg(Analysis.sentiment_score).label("avg_sentiment"),
        )
        .join(MessageCategory, MessageCategory.category_id == Category.id)
        .join(Message, Message.id == MessageCategory.message_id)
        .outerjoin(Analysis, Analysis.message_id == Message.id)
        .where(
            Category.tenant_id == tenant_id,
            Message.tenant_id == tenant_id,
        )
        .group_by(Category.id, Category.name)
        .order_by(func.count(MessageCategory.message_id).desc())
    )

    # Apply date filters if provided
    if start_date:
        query = query.where(Message.received_at >= start_date)
    if end_date:
        query = query.where(Message.received_at <= end_date)

    result = await session.execute(query)
    rows = result.all()

    # Calculate total categorized
    total_categorized = sum(row.count for row in rows)

    # Get total uncategorized (messages without any category)
    uncategorized_base = (
        select(func.count(Message.id))
        .outerjoin(MessageCategory, MessageCategory.message_id == Message.id)
        .where(
            Message.tenant_id == tenant_id,
            MessageCategory.message_id == None,
        )
    )
    if start_date:
        uncategorized_base = uncategorized_base.where(Message.received_at >= start_date)
    if end_date:
        uncategorized_base = uncategorized_base.where(Message.received_at <= end_date)

    uncategorized_result = await session.execute(uncategorized_base)
    total_uncategorized = uncategorized_result.scalar() or 0

    grand_total = total_categorized + total_uncategorized

    data = []
    for row in rows:
        percentage = (row.count / grand_total * 100) if grand_total > 0 else 0
        data.append(
            CategoryBreakdown(
                category_id=row[0],
                category_name=row[1],
                count=row.count,
                percentage=round(percentage, 1),
                avg_sentiment=float(row.avg_sentiment) if row.avg_sentiment else None,
            )
        )

    return CategoryBreakdownResponse(
        data=data,
        total_categorized=total_categorized,
        total_uncategorized=total_uncategorized,
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

    # Apply sentiment filter
    if sentiment_filter:
        if sentiment_filter == "positive":
            query = query.where(Contact.avg_sentiment > 0.3)
        elif sentiment_filter == "negative":
            query = query.where(Contact.avg_sentiment < -0.3)
        elif sentiment_filter == "neutral":
            query = query.where(Contact.avg_sentiment.between(-0.3, 0.3))

    # Apply sorting
    if sort_by == "message_count":
        query = query.order_by(Contact.message_count.desc())
    elif sort_by == "avg_sentiment":
        query = query.order_by(Contact.avg_sentiment.desc())
    elif sort_by == "last_contact":
        query = query.order_by(Contact.last_contact_at.desc())

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

    # Base query conditions
    base_conditions = [Message.tenant_id == tenant_id]
    if start_date:
        base_conditions.append(Message.received_at >= start_date)
    if end_date:
        base_conditions.append(Message.received_at <= end_date)

    # Count campaign messages with sentiment
    campaign_query = (
        select(
            func.count(Message.id),
            func.avg(Analysis.sentiment_score),
        )
        .outerjoin(Analysis, Analysis.message_id == Message.id)
        .where(*base_conditions, Message.is_template_match == True)
    )
    campaign_result = await session.execute(campaign_query)
    campaign_row = campaign_result.first()
    campaign_count = campaign_row[0] or 0
    campaign_sentiment = float(campaign_row[1]) if campaign_row[1] else None

    # Count organic messages with sentiment
    organic_query = (
        select(
            func.count(Message.id),
            func.avg(Analysis.sentiment_score),
        )
        .outerjoin(Analysis, Analysis.message_id == Message.id)
        .where(*base_conditions, Message.is_template_match == False)
    )
    organic_result = await session.execute(organic_query)
    organic_row = organic_result.first()
    organic_count = organic_row[0] or 0
    organic_sentiment = float(organic_row[1]) if organic_row[1] else None

    total = campaign_count + organic_count

    return {
        "campaign_messages": {
            "count": campaign_count,
            "avg_sentiment": campaign_sentiment,
        },
        "organic_messages": {
            "count": organic_count,
            "avg_sentiment": organic_sentiment,
        },
        "campaign_percentage": (
            round(campaign_count / total * 100, 1)
            if total > 0
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
    from app.models.contact import CustomFieldDefinition, ContactFieldValue

    # Verify field belongs to tenant
    field_result = await session.execute(
        select(CustomFieldDefinition).where(
            CustomFieldDefinition.id == field_id,
            CustomFieldDefinition.tenant_id == current_user.tenant_id,
        )
    )
    field = field_result.scalars().first()

    if not field:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom field not found",
        )

    # Query contacts grouped by field value
    # This handles text and select fields
    query = (
        select(
            func.coalesce(ContactFieldValue.value_text, ContactFieldValue.value_option).label("value"),
            func.count(Contact.id).label("contact_count"),
            func.sum(Contact.message_count).label("message_count"),
            func.avg(Contact.avg_sentiment).label("avg_sentiment"),
        )
        .join(Contact, Contact.id == ContactFieldValue.contact_id)
        .where(
            ContactFieldValue.field_definition_id == field_id,
            Contact.tenant_id == current_user.tenant_id,
        )
        .group_by(func.coalesce(ContactFieldValue.value_text, ContactFieldValue.value_option))
        .order_by(func.sum(Contact.message_count).desc())
    )

    result = await session.execute(query)
    rows = result.all()

    breakdown = []
    for row in rows:
        breakdown.append({
            "value": row.value,
            "contact_count": row.contact_count or 0,
            "message_count": row.message_count or 0,
            "avg_sentiment": float(row.avg_sentiment) if row.avg_sentiment else None,
        })

    return {
        "field_id": field_id,
        "field_name": field.name,
        "field_type": field.field_type,
        "breakdown": breakdown,
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
    tenant_id = current_user.tenant_id

    # Build query for processing time calculation
    base_conditions = [
        Message.tenant_id == tenant_id,
        Message.processed_at != None,
    ]
    if start_date:
        base_conditions.append(Message.received_at >= start_date)
    if end_date:
        base_conditions.append(Message.received_at <= end_date)

    # Average processing time in seconds
    avg_query = (
        select(
            func.avg(func.extract("epoch", Message.processed_at - Message.received_at)),
            func.count(),
        )
        .where(*base_conditions)
    )
    avg_result = await session.execute(avg_query)
    avg_row = avg_result.first()
    avg_time = float(avg_row[0]) if avg_row[0] else None
    processed_count = avg_row[1] or 0

    # Pending messages
    pending_conditions = [Message.tenant_id == tenant_id, Message.processing_status == "pending"]
    if start_date:
        pending_conditions.append(Message.received_at >= start_date)
    if end_date:
        pending_conditions.append(Message.received_at <= end_date)

    pending_result = await session.execute(
        select(func.count()).where(*pending_conditions)
    )
    pending_count = pending_result.scalar() or 0

    return {
        "avg_processing_time_seconds": round(avg_time, 2) if avg_time else None,
        "median_processing_time_seconds": None,  # Would need window functions
        "p95_processing_time_seconds": None,  # Would need percentile calculations
        "messages_processed": processed_count,
        "messages_pending": pending_count,
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
    import uuid

    valid_datasets = ["messages", "contacts", "analytics"]
    if request.dataset not in valid_datasets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid dataset. Valid options: {', '.join(valid_datasets)}",
        )

    valid_formats = ["csv", "json"]
    if request.format not in valid_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid format. Valid options: {', '.join(valid_formats)}",
        )

    # Generate job ID
    job_id = str(uuid.uuid4())

    # TODO: Queue export job for async processing
    # For now, return placeholder

    return {
        "job_id": job_id,
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
    # TODO: Look up job status from job queue

    return {
        "job_id": job_id,
        "status": "pending",
        "download_url": None,
        "expires_at": None,
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

    tenant_id = auth.tenant_id
    offset = (page - 1) * page_size

    if dataset_name == "messages_summary":
        # Messages with sentiment
        query = (
            select(
                Message.id,
                Message.sender_email,
                Message.subject,
                Message.source,
                Message.received_at,
                Message.processing_status,
                Message.is_template_match,
                Analysis.sentiment_score,
                Analysis.sentiment_label,
                Analysis.urgency_score,
            )
            .outerjoin(Analysis, Analysis.message_id == Message.id)
            .where(Message.tenant_id == tenant_id)
            .order_by(Message.received_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        count_result = await session.execute(
            select(func.count()).where(Message.tenant_id == tenant_id)
        )
        total = count_result.scalar() or 0

        result = await session.execute(query)
        data = [
            {
                "id": str(row[0]),
                "sender_email": row[1],
                "subject": row[2],
                "source": row[3],
                "received_at": row[4].isoformat() if row[4] else None,
                "processing_status": row[5],
                "is_template_match": row[6],
                "sentiment_score": float(row[7]) if row[7] else None,
                "sentiment_label": row[8],
                "urgency_score": float(row[9]) if row[9] else None,
            }
            for row in result.all()
        ]

    elif dataset_name == "contact_analytics":
        query = (
            select(Contact)
            .where(Contact.tenant_id == tenant_id)
            .order_by(Contact.message_count.desc())
            .offset(offset)
            .limit(page_size)
        )

        count_result = await session.execute(
            select(func.count()).where(Contact.tenant_id == tenant_id)
        )
        total = count_result.scalar() or 0

        result = await session.execute(query)
        data = [
            {
                "id": str(c.id),
                "email": c.email,
                "name": c.name,
                "message_count": c.message_count,
                "avg_sentiment": c.avg_sentiment,
                "first_contact_at": c.first_contact_at.isoformat() if c.first_contact_at else None,
                "last_contact_at": c.last_contact_at.isoformat() if c.last_contact_at else None,
            }
            for c in result.scalars().all()
        ]

    elif dataset_name == "campaign_summary":
        query = (
            select(Campaign)
            .where(Campaign.tenant_id == tenant_id)
            .order_by(Campaign.last_seen_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        count_result = await session.execute(
            select(func.count()).where(Campaign.tenant_id == tenant_id)
        )
        total = count_result.scalar() or 0

        result = await session.execute(query)
        data = [
            {
                "id": str(c.id),
                "name": c.name,
                "status": c.status,
                "detection_type": c.detection_type,
                "message_count": c.message_count,
                "unique_senders": c.unique_senders,
                "source_organization": c.source_organization,
                "first_seen_at": c.first_seen_at.isoformat() if c.first_seen_at else None,
                "last_seen_at": c.last_seen_at.isoformat() if c.last_seen_at else None,
            }
            for c in result.scalars().all()
        ]

    else:
        # For sentiment_trends and category_breakdown, return empty for now
        # These would need different query structures
        data = []
        total = 0

    return {
        "dataset": dataset_name,
        "data": data,
        "page": page,
        "page_size": page_size,
        "total": total,
    }
