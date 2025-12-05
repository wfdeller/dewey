"""Email template rendering with variable substitution."""

import re
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from jinja2 import Environment, BaseLoader, StrictUndefined, UndefinedError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact
from app.models.form import Form
from app.models.message import Message
from app.models.tenant import Tenant
from app.services import form_links as form_links_service


class TemplateUndefined(StrictUndefined):
    """Custom undefined that provides helpful error messages."""

    def _fail_with_undefined_error(self, *args, **kwargs):
        raise UndefinedError(f"Template variable '{self._undefined_name}' is not defined")


# Create Jinja2 environment with strict undefined handling
jinja_env = Environment(
    loader=BaseLoader(),
    undefined=TemplateUndefined,
    autoescape=True,
)


def _parse_first_name(full_name: str | None) -> str:
    """Extract first name from full name."""
    if not full_name:
        return ""
    parts = full_name.strip().split()
    return parts[0] if parts else ""


def _format_datetime(dt: datetime | None, format_str: str = "%B %d, %Y") -> str:
    """Format a datetime for display."""
    if not dt:
        return ""
    return dt.strftime(format_str)


# Add custom filters
jinja_env.filters["first_name"] = _parse_first_name
jinja_env.filters["format_date"] = _format_datetime


class TemplateContext:
    """Context object for template rendering with all available variables."""

    def __init__(
        self,
        contact: Contact | None = None,
        form: Form | None = None,
        form_link_url: str | None = None,
        form_link_expires_at: datetime | None = None,
        message: Message | None = None,
        tenant: Tenant | None = None,
        custom_fields: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
    ):
        self.contact = contact
        self.form = form
        self.form_link_url = form_link_url
        self.form_link_expires_at = form_link_expires_at
        self.message = message
        self.tenant = tenant
        self.custom_fields = custom_fields or {}
        self.extra = extra or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary for Jinja2 rendering."""
        context = {}

        # Contact variables
        if self.contact:
            context["contact"] = {
                "name": self.contact.name or "",
                "first_name": _parse_first_name(self.contact.name),
                "email": self.contact.email,
                "phone": self.contact.phone or "",
            }
        else:
            context["contact"] = {
                "name": "",
                "first_name": "",
                "email": "",
                "phone": "",
            }

        # Form variables
        if self.form:
            context["form"] = {
                "name": self.form.name,
                "description": self.form.description or "",
            }
        else:
            context["form"] = {"name": "", "description": ""}

        # Form link variables
        context["form_link"] = {
            "url": self.form_link_url or "",
            "expires_at": _format_datetime(self.form_link_expires_at) if self.form_link_expires_at else "",
        }
        # Shortcut for common usage: {{form_link}} instead of {{form_link.url}}
        context["form_link_url"] = self.form_link_url or ""

        # Message variables (for auto-replies)
        if self.message:
            context["message"] = {
                "subject": self.message.subject or "",
                "sender_name": self.message.sender_name or "",
                "sender_email": self.message.sender_email or "",
                "received_at": _format_datetime(self.message.received_at),
            }
        else:
            context["message"] = {
                "subject": "",
                "sender_name": "",
                "sender_email": "",
                "received_at": "",
            }

        # Tenant variables
        if self.tenant:
            context["tenant"] = {
                "name": self.tenant.name,
            }
        else:
            context["tenant"] = {"name": ""}

        # Custom fields
        context["custom"] = self.custom_fields

        # Extra variables
        context.update(self.extra)

        return context


def render_template(
    template_string: str,
    context: TemplateContext,
    strict: bool = False,
) -> str:
    """Render a template string with the given context.

    Args:
        template_string: The template string with {{variable}} placeholders
        context: TemplateContext with all available variables
        strict: If True, raise error on undefined variables. If False, leave them empty.

    Returns:
        Rendered template string
    """
    if strict:
        env = jinja_env
    else:
        # Create a permissive environment that replaces undefined with empty string
        env = Environment(
            loader=BaseLoader(),
            undefined=lambda *args, **kwargs: "",
            autoescape=True,
        )
        env.filters["first_name"] = _parse_first_name
        env.filters["format_date"] = _format_datetime

    template = env.from_string(template_string)
    return template.render(context.to_dict())


def render_subject_and_body(
    subject: str,
    body_html: str,
    body_text: str | None,
    context: TemplateContext,
    strict: bool = False,
) -> tuple[str, str, str | None]:
    """Render subject and body templates.

    Returns:
        Tuple of (rendered_subject, rendered_body_html, rendered_body_text)
    """
    rendered_subject = render_template(subject, context, strict=strict)
    rendered_html = render_template(body_html, context, strict=strict)
    rendered_text = render_template(body_text, context, strict=strict) if body_text else None

    return rendered_subject, rendered_html, rendered_text


async def create_form_link_for_template(
    session: AsyncSession,
    form_id: UUID,
    contact_id: UUID,
    is_single_use: bool = True,
    expires_days: int | None = 7,
    base_url: str = "",
    tenant_slug: str = "",
    form_slug: str = "",
) -> tuple[str, datetime | None]:
    """Create a form link and return the full URL.

    Args:
        session: Database session
        form_id: Form to link to
        contact_id: Contact to pre-identify
        is_single_use: Whether the link should be single-use
        expires_days: Days until expiration (None for no expiration)
        base_url: Base URL for the application (e.g., "https://app.dewey.io")
        tenant_slug: Tenant's URL slug
        form_slug: Form's URL slug

    Returns:
        Tuple of (full_url, expires_at)
    """
    expires_at = None
    if expires_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_days)

    link = await form_links_service.create_form_link(
        session=session,
        form_id=form_id,
        contact_id=contact_id,
        is_single_use=is_single_use,
        expires_at=expires_at,
    )

    # Construct full URL
    # Format: {base_url}/f/{tenant_slug}/{form_slug}?t={token}
    full_url = f"{base_url}/f/{tenant_slug}/{form_slug}?t={link.token}"

    return full_url, expires_at


def extract_template_variables(template_string: str) -> list[str]:
    """Extract all variable names from a template string.

    Useful for UI to show which variables are used.
    """
    # Match {{variable}} or {{variable.property}}
    pattern = r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)\s*\}\}"
    matches = re.findall(pattern, template_string)
    return list(set(matches))


def validate_template(template_string: str) -> tuple[bool, str | None]:
    """Validate a template string for syntax errors.

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        jinja_env.from_string(template_string)
        return True, None
    except Exception as e:
        return False, str(e)
