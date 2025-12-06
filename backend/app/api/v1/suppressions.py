"""Email suppression list management endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func

from app.core.database import get_session
from app.api.v1.deps import PermissionChecker
from app.models.user import User, Permissions
from app.models.email import (
    EmailSuppression,
    EmailSuppressionCreate,
    EmailSuppressionRead,
    SuppressionType,
)
from app.models.contact import Contact

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================


class SuppressionListResponse(BaseModel):
    """Paginated suppression list response."""

    items: list[EmailSuppressionRead]
    total: int
    page: int
    page_size: int
    pages: int


class SuppressionStatsResponse(BaseModel):
    """Suppression statistics summary."""

    total_suppressed: int
    by_type: dict[str, int]
    recent_additions: int  # Last 7 days


class CheckSuppressionResponse(BaseModel):
    """Response for checking if an email is suppressed."""

    email: str
    is_suppressed: bool
    suppression_type: str | None = None
    suppressed_at: datetime | None = None
    is_global: bool | None = None


class BulkSuppressionRequest(BaseModel):
    """Request to add multiple suppressions."""

    emails: list[EmailStr]
    suppression_type: str = "manual"
    is_global: bool = True


class BulkSuppressionResponse(BaseModel):
    """Response for bulk suppression."""

    added: int
    skipped: int  # Already suppressed
    emails_added: list[str]
    emails_skipped: list[str]


# =============================================================================
# Suppression CRUD Endpoints
# =============================================================================


@router.get("", response_model=SuppressionListResponse)
async def list_suppressions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    suppression_type: SuppressionType | None = Query(None, alias="type"),
    search: str | None = Query(None, description="Search by email"),
    is_active: bool = Query(True, description="Filter by active status"),
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_READ)),
    session: AsyncSession = Depends(get_session),
) -> SuppressionListResponse:
    """
    List email suppressions.

    Suppressions include unsubscribes, bounces, complaints, and manual blocks.
    """
    query = select(EmailSuppression).where(
        EmailSuppression.tenant_id == current_user.tenant_id,
        EmailSuppression.is_active == is_active,
    )

    # Apply type filter
    if suppression_type:
        query = query.where(EmailSuppression.suppression_type == suppression_type)

    # Apply search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.where(EmailSuppression.email.ilike(search_pattern))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and ordering
    offset = (page - 1) * page_size
    query = query.order_by(EmailSuppression.suppressed_at.desc()).offset(offset).limit(page_size)

    result = await session.execute(query)
    suppressions = result.scalars().all()

    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return SuppressionListResponse(
        items=[EmailSuppressionRead.model_validate(s) for s in suppressions],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("", response_model=EmailSuppressionRead, status_code=status.HTTP_201_CREATED)
async def create_suppression(
    request: EmailSuppressionCreate,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> EmailSuppressionRead:
    """
    Manually add an email to the suppression list.

    This prevents the email from receiving any campaign emails.
    """
    # Check if already suppressed
    existing = await session.execute(
        select(EmailSuppression).where(
            EmailSuppression.tenant_id == current_user.tenant_id,
            EmailSuppression.email == request.email.lower(),
            EmailSuppression.is_active == True,  # noqa: E712
        )
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already suppressed",
        )

    # Try to find associated contact
    contact_result = await session.execute(
        select(Contact).where(
            Contact.tenant_id == current_user.tenant_id,
            Contact.email == request.email.lower(),
        )
    )
    contact = contact_result.scalars().first()

    suppression = EmailSuppression(
        tenant_id=current_user.tenant_id,
        email=request.email.lower(),
        contact_id=contact.id if contact else None,
        suppression_type=request.suppression_type,
        is_global=request.is_global,
        campaign_id=request.campaign_id,
        suppressed_at=datetime.utcnow(),
    )

    session.add(suppression)
    await session.commit()
    await session.refresh(suppression)

    return EmailSuppressionRead.model_validate(suppression)


@router.post("/bulk", response_model=BulkSuppressionResponse)
async def bulk_create_suppressions(
    request: BulkSuppressionRequest,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> BulkSuppressionResponse:
    """
    Add multiple emails to the suppression list.

    Useful for importing suppression lists or blocking multiple addresses.
    """
    if len(request.emails) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 1000 emails per request",
        )

    # Get existing suppressed emails
    existing_result = await session.execute(
        select(EmailSuppression.email).where(
            EmailSuppression.tenant_id == current_user.tenant_id,
            EmailSuppression.email.in_([e.lower() for e in request.emails]),
            EmailSuppression.is_active == True,  # noqa: E712
        )
    )
    existing_emails = {row[0] for row in existing_result.all()}

    emails_added = []
    emails_skipped = []

    for email in request.emails:
        normalized_email = email.lower()
        if normalized_email in existing_emails:
            emails_skipped.append(normalized_email)
            continue

        suppression = EmailSuppression(
            tenant_id=current_user.tenant_id,
            email=normalized_email,
            suppression_type=request.suppression_type,
            is_global=request.is_global,
            suppressed_at=datetime.utcnow(),
        )
        session.add(suppression)
        emails_added.append(normalized_email)

    await session.commit()

    return BulkSuppressionResponse(
        added=len(emails_added),
        skipped=len(emails_skipped),
        emails_added=emails_added,
        emails_skipped=emails_skipped,
    )


@router.get("/{suppression_id}", response_model=EmailSuppressionRead)
async def get_suppression(
    suppression_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_READ)),
    session: AsyncSession = Depends(get_session),
) -> EmailSuppressionRead:
    """Get a specific suppression entry."""
    result = await session.execute(
        select(EmailSuppression).where(
            EmailSuppression.id == suppression_id,
            EmailSuppression.tenant_id == current_user.tenant_id,
        )
    )
    suppression = result.scalars().first()

    if not suppression:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suppression not found",
        )

    return EmailSuppressionRead.model_validate(suppression)


@router.delete("/{suppression_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_suppression(
    suppression_id: UUID,
    reason: str | None = Query(None, description="Reason for removal"),
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Remove an email from the suppression list.

    This soft-deletes the suppression, keeping an audit trail.
    The email will be able to receive campaign emails again.
    """
    result = await session.execute(
        select(EmailSuppression).where(
            EmailSuppression.id == suppression_id,
            EmailSuppression.tenant_id == current_user.tenant_id,
        )
    )
    suppression = result.scalars().first()

    if not suppression:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suppression not found",
        )

    if not suppression.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Suppression is already removed",
        )

    # Soft delete with audit trail
    suppression.is_active = False
    suppression.removed_at = datetime.utcnow()
    suppression.removed_by_id = current_user.id
    suppression.removal_reason = reason

    await session.commit()


# =============================================================================
# Check & Stats Endpoints
# =============================================================================


@router.get("/check/{email}", response_model=CheckSuppressionResponse)
async def check_suppression(
    email: str,
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_READ)),
    session: AsyncSession = Depends(get_session),
) -> CheckSuppressionResponse:
    """
    Check if an email address is suppressed.

    Returns suppression details if the email is blocked.
    """
    result = await session.execute(
        select(EmailSuppression).where(
            EmailSuppression.tenant_id == current_user.tenant_id,
            EmailSuppression.email == email.lower(),
            EmailSuppression.is_active == True,  # noqa: E712
        )
    )
    suppression = result.scalars().first()

    if suppression:
        return CheckSuppressionResponse(
            email=email.lower(),
            is_suppressed=True,
            suppression_type=suppression.suppression_type,
            suppressed_at=suppression.suppressed_at,
            is_global=suppression.is_global,
        )
    else:
        return CheckSuppressionResponse(
            email=email.lower(),
            is_suppressed=False,
        )


@router.get("/stats/summary", response_model=SuppressionStatsResponse)
async def get_suppression_stats(
    current_user: User = Depends(PermissionChecker(Permissions.ANALYTICS_READ)),
    session: AsyncSession = Depends(get_session),
) -> SuppressionStatsResponse:
    """Get summary statistics for email suppressions."""
    tenant_id = current_user.tenant_id

    # Count by suppression type
    type_result = await session.execute(
        select(EmailSuppression.suppression_type, func.count(EmailSuppression.id))
        .where(
            EmailSuppression.tenant_id == tenant_id,
            EmailSuppression.is_active == True,  # noqa: E712
        )
        .group_by(EmailSuppression.suppression_type)
    )
    type_counts = {row[0]: row[1] for row in type_result.all()}

    # Count recent additions (last 7 days)
    from datetime import timedelta

    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_result = await session.execute(
        select(func.count(EmailSuppression.id)).where(
            EmailSuppression.tenant_id == tenant_id,
            EmailSuppression.is_active == True,  # noqa: E712
            EmailSuppression.suppressed_at >= seven_days_ago,
        )
    )
    recent_additions = recent_result.scalar() or 0

    return SuppressionStatsResponse(
        total_suppressed=sum(type_counts.values()),
        by_type=type_counts,
        recent_additions=recent_additions,
    )


# =============================================================================
# Search Endpoint
# =============================================================================


@router.post("/search", response_model=list[CheckSuppressionResponse])
async def search_suppressions(
    emails: list[EmailStr],
    current_user: User = Depends(PermissionChecker(Permissions.MESSAGES_READ)),
    session: AsyncSession = Depends(get_session),
) -> list[CheckSuppressionResponse]:
    """
    Check multiple emails for suppression status.

    Returns suppression status for each email in the list.
    """
    if len(emails) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 emails per request",
        )

    normalized_emails = [e.lower() for e in emails]

    # Get all suppressions for these emails
    result = await session.execute(
        select(EmailSuppression).where(
            EmailSuppression.tenant_id == current_user.tenant_id,
            EmailSuppression.email.in_(normalized_emails),
            EmailSuppression.is_active == True,  # noqa: E712
        )
    )
    suppressions = {s.email: s for s in result.scalars().all()}

    responses = []
    for email in normalized_emails:
        if email in suppressions:
            s = suppressions[email]
            responses.append(
                CheckSuppressionResponse(
                    email=email,
                    is_suppressed=True,
                    suppression_type=s.suppression_type,
                    suppressed_at=s.suppressed_at,
                    is_global=s.is_global,
                )
            )
        else:
            responses.append(
                CheckSuppressionResponse(
                    email=email,
                    is_suppressed=False,
                )
            )

    return responses
