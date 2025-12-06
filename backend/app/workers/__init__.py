"""Background worker processes package.

This module contains ARQ task definitions and worker configuration.

To run the worker:
    python -m app.workers.worker

Tasks available:
    - process_voter_import: Process CSV voter file imports
    - export_contacts: Export contacts to file
    - send_campaign_emails: Send campaign emails
    - generate_campaign_recommendations: Generate AI-powered campaign recommendations
    - check_scheduled_campaigns: Check and start scheduled campaigns
    - analyze_message: Analyze message content using AI
"""

from app.workers.tasks import (
    process_voter_import,
    export_contacts,
    send_campaign_emails,
    generate_campaign_recommendations,
    check_scheduled_campaigns,
    analyze_message,
)
from app.workers.worker import WorkerSettings

__all__ = [
    "process_voter_import",
    "export_contacts",
    "send_campaign_emails",
    "generate_campaign_recommendations",
    "check_scheduled_campaigns",
    "analyze_message",
    "WorkerSettings",
]
