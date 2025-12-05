"""Background worker processes package.

This module contains ARQ task definitions and worker configuration.

To run the worker:
    python -m app.workers.worker

Tasks available:
    - process_voter_import: Process CSV voter file imports
    - export_contacts: Export contacts to file (TODO)
    - send_bulk_email: Send bulk campaign emails (TODO)
"""

from app.workers.tasks import process_voter_import, export_contacts, send_bulk_email
from app.workers.worker import WorkerSettings

__all__ = [
    "process_voter_import",
    "export_contacts",
    "send_bulk_email",
    "WorkerSettings",
]
