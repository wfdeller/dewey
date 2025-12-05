"""ARQ task definitions for background job processing."""

from datetime import datetime
from uuid import UUID

import structlog
from sqlmodel import select

from app.core.database import async_session_maker
from app.models.job import Job
from app.services.voter_import import VoterImportService


logger = structlog.get_logger()


async def _mark_job_failed(job_id: str, tenant_id: str, error_message: str) -> None:
    """Mark a job as failed in the database.

    Uses a separate session to ensure the failure is recorded even if
    the main session was rolled back.
    """
    try:
        async with async_session_maker() as session:
            result = await session.execute(
                select(Job).where(
                    Job.id == UUID(job_id),
                    Job.tenant_id == UUID(tenant_id),
                )
            )
            job = result.scalars().first()
            if job:
                job.status = "failed"
                job.error_message = error_message[:1000]  # Truncate long errors
                job.completed_at = datetime.utcnow()
                await session.commit()
                logger.info("Marked job as failed", job_id=job_id)
    except Exception as e:
        logger.error("Failed to mark job as failed", job_id=job_id, error=str(e))


async def process_voter_import(ctx: dict, job_id: str, tenant_id: str) -> dict:
    """ARQ task for processing voter file import.

    Args:
        ctx: ARQ context (contains job info, redis connection)
        job_id: The Job UUID as string
        tenant_id: The tenant UUID as string

    Returns:
        Result dictionary with status and job_id
    """
    logger.info(
        "Starting voter import task",
        job_id=job_id,
        tenant_id=tenant_id,
        arq_job_id=ctx.get("job_id"),
    )

    try:
        async with async_session_maker() as session:
            service = VoterImportService(session, UUID(tenant_id))
            await service.process_import(UUID(job_id))

        logger.info(
            "Completed voter import task",
            job_id=job_id,
            tenant_id=tenant_id,
        )

        return {"status": "completed", "job_id": job_id}

    except Exception as e:
        error_msg = str(e)
        logger.error(
            "Voter import task failed",
            job_id=job_id,
            tenant_id=tenant_id,
            error=error_msg,
        )
        # Mark the job as failed in a separate session
        await _mark_job_failed(job_id, tenant_id, error_msg)
        # Don't re-raise - job is marked as failed, no point in ARQ retrying
        return {"status": "failed", "job_id": job_id, "error": error_msg}


async def export_contacts(
    ctx: dict, job_id: str, tenant_id: str, filters: dict | None = None
) -> dict:
    """ARQ task for exporting contacts.

    Args:
        ctx: ARQ context
        job_id: The Job UUID as string
        tenant_id: The tenant UUID as string
        filters: Optional filter criteria for contacts

    Returns:
        Result dictionary with status and job_id

    TODO: Implement contact export functionality
    """
    logger.info(
        "Contact export task placeholder",
        job_id=job_id,
        tenant_id=tenant_id,
        filters=filters,
    )
    return {"status": "not_implemented", "job_id": job_id}


async def send_bulk_email(
    ctx: dict, job_id: str, tenant_id: str, campaign_id: str
) -> dict:
    """ARQ task for sending bulk emails for a campaign.

    Args:
        ctx: ARQ context
        job_id: The Job UUID as string
        tenant_id: The tenant UUID as string
        campaign_id: The campaign UUID as string

    Returns:
        Result dictionary with status and job_id

    TODO: Implement bulk email sending functionality
    """
    logger.info(
        "Bulk email task placeholder",
        job_id=job_id,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
    )
    return {"status": "not_implemented", "job_id": job_id}
