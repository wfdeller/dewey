"""ARQ worker configuration and entry point.

Run with: python -m app.workers.worker
"""

import asyncio
from typing import Any

import structlog
from arq import cron
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.workers.tasks import (
    process_voter_import,
    export_contacts,
    send_campaign_emails,
    generate_campaign_recommendations,
    check_scheduled_campaigns,
    analyze_message,
)


logger = structlog.get_logger()


async def startup(ctx: dict) -> None:
    """Called when worker starts up."""
    logger.info("ARQ worker starting up")


async def shutdown(ctx: dict) -> None:
    """Called when worker shuts down."""
    logger.info("ARQ worker shutting down")


async def on_job_start(ctx: dict) -> None:
    """Called before a job starts processing."""
    logger.debug(
        "Job starting",
        job_id=ctx.get("job_id"),
        job_try=ctx.get("job_try"),
    )


async def on_job_end(ctx: dict) -> None:
    """Called after a job completes (success or failure)."""
    logger.debug(
        "Job ended",
        job_id=ctx.get("job_id"),
        job_try=ctx.get("job_try"),
    )


class WorkerSettings:
    """ARQ worker configuration.

    This class defines all the settings for the ARQ worker process.
    ARQ looks for a class with this exact name when starting a worker.
    """

    # Task functions that this worker can execute
    functions = [
        process_voter_import,
        export_contacts,
        send_campaign_emails,
        generate_campaign_recommendations,
        check_scheduled_campaigns,
        analyze_message,
    ]

    # Redis connection settings - loaded at import time from environment
    redis_settings = RedisSettings.from_dsn(str(get_settings().redis_url))

    # Retry configuration
    max_tries = 3  # Maximum retry attempts
    retry_jobs = True  # Enable automatic retries

    # Job timeout (1 hour default for large imports)
    job_timeout = 3600

    # Maximum concurrent jobs per worker
    # Start with 1 for simplicity, can be increased via settings
    max_jobs = 1

    # Health check interval (seconds)
    health_check_interval = 30

    # Queue name (default is 'arq:queue')
    queue_name = "arq:queue"

    # Lifecycle hooks
    on_startup = startup
    on_shutdown = shutdown
    on_job_start = on_job_start
    on_job_end = on_job_end

    # Scheduled tasks (cron jobs)
    cron_jobs = [
        # Check for scheduled campaigns every 15 minutes
        cron(check_scheduled_campaigns, minute={0, 15, 30, 45}),
    ]


def run_worker() -> None:
    """Run the ARQ worker."""
    from arq import run_worker as arq_run_worker

    logger.info("Starting ARQ worker process")
    arq_run_worker(WorkerSettings)


if __name__ == "__main__":
    run_worker()
