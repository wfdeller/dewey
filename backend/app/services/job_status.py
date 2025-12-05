"""Job status tracking via Redis for real-time progress updates."""

import json
from uuid import UUID

import redis.asyncio as redis

from app.core.redis import get_redis_client


# Key prefix for job progress
JOB_PROGRESS_PREFIX = "job_progress:"
JOB_PROGRESS_TTL = 3600  # 1 hour TTL


async def update_job_progress(
    job_id: UUID,
    progress: dict,
) -> None:
    """
    Update job progress in Redis for real-time polling.

    Args:
        job_id: The job UUID
        progress: Dict with progress fields like:
            {
                "status": "processing",
                "rows_processed": 100,
                "rows_created": 50,
                "rows_updated": 30,
                "rows_skipped": 15,
                "rows_errored": 5,
                "total_rows": 1000,
                "percent_complete": 10.0,
                "current_row": 100,
                "last_error": "..."
            }
    """
    client = get_redis_client()
    key = f"{JOB_PROGRESS_PREFIX}{job_id}"

    try:
        await client.setex(
            key,
            JOB_PROGRESS_TTL,
            json.dumps(progress),
        )
    except redis.RedisError:
        # Fail silently - progress updates are best effort
        pass


async def get_job_progress(job_id: UUID) -> dict | None:
    """
    Get current job progress from Redis.

    Args:
        job_id: The job UUID

    Returns:
        Progress dict or None if not found
    """
    client = get_redis_client()
    key = f"{JOB_PROGRESS_PREFIX}{job_id}"

    try:
        data = await client.get(key)
        if data:
            return json.loads(data)
        return None
    except redis.RedisError:
        return None


async def delete_job_progress(job_id: UUID) -> None:
    """
    Delete job progress from Redis after completion.

    Args:
        job_id: The job UUID
    """
    client = get_redis_client()
    key = f"{JOB_PROGRESS_PREFIX}{job_id}"

    try:
        await client.delete(key)
    except redis.RedisError:
        pass


async def set_job_error(job_id: UUID, error_message: str) -> None:
    """
    Set job error state in Redis.

    Args:
        job_id: The job UUID
        error_message: The error message
    """
    await update_job_progress(
        job_id,
        {
            "status": "failed",
            "error_message": error_message,
        },
    )
