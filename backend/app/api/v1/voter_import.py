"""Voter file import API endpoints."""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_session
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.models.job import JobRead, JobProgress, JobConfirmMappings, Job
from app.services.voter_import import VoterImportService, MATCHING_STRATEGIES
from app.services.job_status import get_job_progress


router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class AnalysisResponse(BaseModel):
    """Response from file analysis."""

    job_id: str
    headers: list[str]
    suggested_mappings: dict
    vote_history_columns: list[str]
    suggested_matching_strategy: str
    matching_strategy_reason: str
    total_rows: int


class JobListResponse(BaseModel):
    """Paginated list of jobs."""

    items: list[JobRead]
    total: int
    limit: int
    offset: int


class MatchingStrategiesResponse(BaseModel):
    """Available matching strategies."""

    strategies: dict[str, str]


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/strategies", response_model=MatchingStrategiesResponse)
async def get_matching_strategies() -> MatchingStrategiesResponse:
    """
    Get available matching strategies with descriptions.

    Returns list of strategies that can be used when confirming mappings.
    """
    return MatchingStrategiesResponse(strategies=MATCHING_STRATEGIES)


@router.post("/upload", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> JobRead:
    """
    Upload a CSV voter file for import.

    Creates an import job and saves the file for processing.
    Returns the job ID which can be used to analyze and start the import.
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported",
        )

    # Validate file size (max 50MB)
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds 50MB limit",
        )

    # Reset file position
    await file.seek(0)

    service = VoterImportService(session, current_user.tenant_id)

    try:
        job = await service.create_job(
            file=file.file,
            filename=file.filename,
            user=current_user,
        )
        return JobRead.model_validate(job)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}",
        )


@router.post("/{job_id}/analyze", response_model=AnalysisResponse)
async def analyze_file(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AnalysisResponse:
    """
    Analyze an uploaded file and get AI-suggested field mappings.

    Returns suggested mappings for each column header and a recommended
    matching strategy based on the data quality.
    """
    service = VoterImportService(session, current_user.tenant_id)

    try:
        result = await service.analyze_job(job_id)
        return AnalysisResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}",
        )


@router.get("/{job_id}", response_model=JobRead)
async def get_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> JobRead:
    """
    Get the current status and details of an import job.
    """
    service = VoterImportService(session, current_user.tenant_id)

    try:
        job = await service.get_job(job_id)
        return JobRead.model_validate(job)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/{job_id}/progress", response_model=JobProgress)
async def get_job_progress_endpoint(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> JobProgress:
    """
    Get real-time progress of a running import job.

    Uses Redis for fast polling during active imports.
    Falls back to database if Redis data not available.
    """
    service = VoterImportService(session, current_user.tenant_id)

    try:
        # Verify job exists and belongs to tenant
        job = await service.get_job(job_id)

        # Try Redis first for real-time progress
        progress = await get_job_progress(job_id)

        if progress:
            return JobProgress(
                status=progress.get("status", job.status),
                rows_processed=progress.get("rows_processed", job.rows_processed),
                rows_created=progress.get("rows_created", job.rows_created),
                rows_updated=progress.get("rows_updated", job.rows_updated),
                rows_skipped=progress.get("rows_skipped", job.rows_skipped),
                rows_errored=progress.get("rows_errored", job.rows_errored),
                total_rows=job.total_rows,
                percent_complete=progress.get("percent_complete"),
            )

        # Fall back to database
        percent = (job.rows_processed / job.total_rows) * 100 if job.total_rows else None

        return JobProgress(
            status=job.status,
            rows_processed=job.rows_processed,
            rows_created=job.rows_created,
            rows_updated=job.rows_updated,
            rows_skipped=job.rows_skipped,
            rows_errored=job.rows_errored,
            total_rows=job.total_rows,
            percent_complete=percent,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.patch("/{job_id}/confirm", response_model=JobRead)
async def confirm_mappings(
    job_id: UUID,
    request: JobConfirmMappings,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> JobRead:
    """
    Confirm field mappings and matching strategy before starting import.

    The confirmed_mappings should be a dict mapping CSV headers to contact fields.
    """
    service = VoterImportService(session, current_user.tenant_id)

    try:
        job = await service.confirm_mappings(
            job_id=job_id,
            confirmed_mappings=request.confirmed_mappings,
            matching_strategy=request.matching_strategy,
        )
        return JobRead.model_validate(job)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{job_id}/start", response_model=JobRead)
async def start_import(
    job_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> JobRead:
    """
    Start processing the import job in the background.

    The job must have confirmed mappings before starting.
    Poll the /progress endpoint to track progress.
    """
    service = VoterImportService(session, current_user.tenant_id)

    try:
        job = await service.get_job(job_id)

        if not job.confirmed_mappings:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mappings must be confirmed before starting import",
            )

        if job.status == "processing":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Import is already running",
            )

        if job.status == "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Import has already completed",
            )

        # Start background processing
        # Note: We need to create a new session for the background task
        background_tasks.add_task(_run_import_background, job_id, current_user.tenant_id)

        # Update status
        job.status = "processing"
        await session.commit()
        await session.refresh(job)

        return JobRead.model_validate(job)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Delete an import job and its uploaded file.

    Cannot delete jobs that are currently processing.
    """
    service = VoterImportService(session, current_user.tenant_id)

    try:
        job = await service.get_job(job_id)

        if job.status == "processing":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete a job that is currently processing",
            )

        await service.delete_job(job_id)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("", response_model=JobListResponse)
async def list_jobs(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> JobListResponse:
    """
    List all voter import jobs for the tenant.

    Returns jobs sorted by creation date (newest first).
    """
    service = VoterImportService(session, current_user.tenant_id)

    jobs, total = await service.list_jobs(limit=limit, offset=offset)

    return JobListResponse(
        items=[JobRead.model_validate(job) for job in jobs],
        total=total,
        limit=limit,
        offset=offset,
    )


# =============================================================================
# Background Task
# =============================================================================


async def _run_import_background(job_id: UUID, tenant_id: UUID) -> None:
    """
    Run the import in a background task with its own session.
    """
    from app.core.database import async_session_maker

    async with async_session_maker() as session:
        service = VoterImportService(session, tenant_id)
        try:
            await service.process_import(job_id)
        except Exception as e:
            # Error is logged in the service
            import structlog
            logger = structlog.get_logger()
            logger.error(
                "Background import failed",
                job_id=str(job_id),
                error=str(e),
            )
