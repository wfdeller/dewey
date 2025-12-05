"""Email services package."""

from app.services.email.providers import (
    EmailProvider,
    EmailMessage,
    EmailResult,
    get_email_provider,
)
from app.services.email.template_renderer import render_template
from app.services.email.sender import send_email, send_template_email

__all__ = [
    "EmailProvider",
    "EmailMessage",
    "EmailResult",
    "get_email_provider",
    "render_template",
    "send_email",
    "send_template_email",
]
