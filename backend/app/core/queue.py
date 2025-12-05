"""ARQ task queue client helpers."""

from datetime import timedelta
from typing import Any

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.core.config import get_settings

# Global pool instance (initialized on first use)
_arq_pool: ArqRedis | None = None


async def get_arq_pool() -> ArqRedis:
    """Get or create ARQ Redis connection pool.

    This is a singleton pattern - the pool is created once and reused.
    """
    global _arq_pool
    if _arq_pool is None:
        settings = get_settings()
        redis_settings = RedisSettings.from_dsn(str(settings.redis_url))
        _arq_pool = await create_pool(redis_settings)
    return _arq_pool


async def close_arq_pool() -> None:
    """Close the ARQ connection pool.

    Call this during application shutdown.
    """
    global _arq_pool
    if _arq_pool is not None:
        await _arq_pool.aclose()
        _arq_pool = None


async def enqueue_job(
    task_name: str,
    *args: Any,
    _job_id: str | None = None,
    _defer_by: timedelta | None = None,
    _defer_until: Any | None = None,
    **kwargs: Any,
) -> str | None:
    """Enqueue a job to the ARQ queue.

    Args:
        task_name: Name of the task function to execute
        *args: Positional arguments to pass to the task
        _job_id: Optional unique job ID (for deduplication)
        _defer_by: Optional delay before job starts
        _defer_until: Optional datetime when job should start
        **kwargs: Keyword arguments to pass to the task

    Returns:
        The ARQ job ID if enqueued successfully, None if job already exists
    """
    pool = await get_arq_pool()
    job = await pool.enqueue_job(
        task_name,
        *args,
        _job_id=_job_id,
        _defer_by=_defer_by,
        _defer_until=_defer_until,
        **kwargs,
    )
    return job.job_id if job else None


async def get_job_result(job_id: str) -> Any:
    """Get the result of a completed job.

    Args:
        job_id: The ARQ job ID

    Returns:
        The job result, or None if not found/not complete
    """
    pool = await get_arq_pool()
    job = await pool.job(job_id)
    if job:
        return await job.result(timeout=0)
    return None


async def get_job_status(job_id: str) -> str | None:
    """Get the status of a job.

    Args:
        job_id: The ARQ job ID

    Returns:
        Job status string: 'queued', 'in_progress', 'complete', 'not_found'
    """
    pool = await get_arq_pool()
    job = await pool.job(job_id)
    if job:
        return await job.status()
    return None
