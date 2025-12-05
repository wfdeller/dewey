"""Email sending service that orchestrates template rendering and provider sending."""

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email import (
    EmailTemplate,
    TenantEmailConfig,
    SentEmail,
)
from app.models.contact import Contact
from app.models.form import Form
from app.models.message import Message
from app.models.tenant import Tenant
from app.services.email.providers import (
    EmailMessage,
    EmailResult,
    get_email_provider,
)
from app.services.email.template_renderer import (
    TemplateContext,
    render_subject_and_body,
    create_form_link_for_template,
)

logger = logging.getLogger(__name__)


class EmailSendError(Exception):
    """Exception raised when email sending fails."""

    def __init__(self, message: str, is_retryable: bool = True):
        self.message = message
        self.is_retryable = is_retryable
        super().__init__(message)


async def get_tenant_email_config(
    session: AsyncSession,
    tenant_id: UUID,
) -> TenantEmailConfig | None:
    """Get email configuration for a tenant."""
    result = await session.execute(
        select(TenantEmailConfig).where(
            TenantEmailConfig.tenant_id == tenant_id,
            TenantEmailConfig.is_active == True,
        )
    )
    return result.scalars().first()


async def send_email(
    session: AsyncSession,
    tenant_id: UUID,
    to_email: str,
    to_name: str | None,
    subject: str,
    body_html: str,
    body_text: str | None = None,
    reply_to: str | None = None,
    contact_id: UUID | None = None,
    template_id: UUID | None = None,
    triggered_by: str | None = None,
    workflow_id: UUID | None = None,
    workflow_execution_id: UUID | None = None,
    message_id: UUID | None = None,
    form_submission_id: UUID | None = None,
    form_link_id: UUID | None = None,
) -> SentEmail:
    """Send an email and log it.

    Args:
        session: Database session
        tenant_id: Tenant sending the email
        to_email: Recipient email address
        to_name: Recipient name
        subject: Email subject (already rendered)
        body_html: HTML body (already rendered)
        body_text: Plain text body (already rendered)
        reply_to: Reply-to address
        contact_id: Associated contact
        template_id: Template used (if any)
        triggered_by: What triggered this email (workflow, campaign, manual, form_auto_reply)
        workflow_id: Associated workflow
        workflow_execution_id: Associated workflow execution
        message_id: Original message (for auto-replies)
        form_submission_id: Associated form submission
        form_link_id: Form link included in email

    Returns:
        SentEmail record
    """
    # Get tenant email configuration
    config = await get_tenant_email_config(session, tenant_id)
    if not config:
        raise EmailSendError(
            "No email configuration found for tenant. Please configure email settings.",
            is_retryable=False,
        )

    # Check rate limiting
    now = datetime.utcnow()
    if config.hour_window_start:
        # Reset counter if hour has passed
        hours_elapsed = (now - config.hour_window_start).total_seconds() / 3600
        if hours_elapsed >= 1:
            config.sends_this_hour = 0
            config.hour_window_start = now
    else:
        config.hour_window_start = now

    if config.sends_this_hour >= config.max_sends_per_hour:
        raise EmailSendError(
            f"Rate limit exceeded. Maximum {config.max_sends_per_hour} emails per hour.",
            is_retryable=True,
        )

    # Create sent email record (initially pending)
    sent_email = SentEmail(
        tenant_id=tenant_id,
        template_id=template_id,
        to_email=to_email,
        to_name=to_name,
        contact_id=contact_id,
        subject=subject,
        body_html=body_html,
        body_text=body_text,
        triggered_by=triggered_by,
        workflow_id=workflow_id,
        workflow_execution_id=workflow_execution_id,
        message_id=message_id,
        form_submission_id=form_submission_id,
        form_link_id=form_link_id,
        status="pending",
    )
    session.add(sent_email)

    # Decrypt sensitive config fields (placeholder - implement actual decryption)
    # In production, use proper encryption/decryption
    decrypted_config = _decrypt_config(config.config, config.provider)

    try:
        # Get the appropriate provider
        provider = get_email_provider(
            provider_type=config.provider,
            config=decrypted_config,
            from_email=config.from_email,
            from_name=config.from_name,
        )

        # Build the message
        message = EmailMessage(
            to_email=to_email,
            to_name=to_name,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            reply_to=reply_to or config.reply_to_email,
        )

        # Send the email
        result = await provider.send(message)

        if result.success:
            sent_email.status = "sent"
            sent_email.sent_at = datetime.utcnow()
            sent_email.provider_message_id = result.message_id

            # Update rate limit counter
            config.sends_this_hour += 1
            config.last_send_at = now
            config.last_error = None
        else:
            sent_email.status = "failed"
            sent_email.error_message = result.error
            config.last_error = result.error
            logger.error(f"Failed to send email: {result.error}")

    except Exception as e:
        sent_email.status = "failed"
        sent_email.error_message = str(e)
        config.last_error = str(e)
        logger.exception(f"Error sending email: {e}")

    await session.commit()
    await session.refresh(sent_email)

    if sent_email.status == "failed":
        raise EmailSendError(sent_email.error_message or "Unknown error")

    return sent_email


async def send_template_email(
    session: AsyncSession,
    template_id: UUID,
    contact_id: UUID,
    triggered_by: str = "manual",
    message_id: UUID | None = None,
    form_id_override: UUID | None = None,
    workflow_id: UUID | None = None,
    workflow_execution_id: UUID | None = None,
    form_submission_id: UUID | None = None,
    extra_context: dict | None = None,
    base_url: str = "",
) -> SentEmail:
    """Send an email using a template.

    This is the main entry point for sending templated emails.
    It handles:
    - Loading the template
    - Loading the contact and related data
    - Generating form links if needed
    - Rendering the template
    - Sending via the configured provider
    - Logging the sent email

    Args:
        session: Database session
        template_id: Email template to use
        contact_id: Contact to send to
        triggered_by: What triggered this (workflow, campaign, manual, form_auto_reply)
        message_id: Original message (for auto-replies)
        form_id_override: Override the template's default form for the form link
        workflow_id: Associated workflow
        workflow_execution_id: Associated workflow execution
        form_submission_id: Associated form submission
        extra_context: Additional variables for template rendering
        base_url: Base URL for form links

    Returns:
        SentEmail record
    """
    # Load the template
    template_result = await session.execute(
        select(EmailTemplate).where(EmailTemplate.id == template_id)
    )
    template = template_result.scalars().first()
    if not template:
        raise EmailSendError(f"Template {template_id} not found", is_retryable=False)

    if not template.is_active:
        raise EmailSendError("Template is not active", is_retryable=False)

    # Load the contact
    contact_result = await session.execute(
        select(Contact).where(Contact.id == contact_id)
    )
    contact = contact_result.scalars().first()
    if not contact:
        raise EmailSendError(f"Contact {contact_id} not found", is_retryable=False)

    # Load the tenant
    tenant_result = await session.execute(
        select(Tenant).where(Tenant.id == template.tenant_id)
    )
    tenant = tenant_result.scalars().first()

    # Load the original message if this is an auto-reply
    message = None
    if message_id:
        message_result = await session.execute(
            select(Message).where(Message.id == message_id)
        )
        message = message_result.scalars().first()

    # Determine form for form link
    form_id = form_id_override or template.default_form_id
    form = None
    form_link_url = None
    form_link_expires_at = None
    form_link_id = None

    if form_id:
        form_result = await session.execute(
            select(Form).where(Form.id == form_id)
        )
        form = form_result.scalars().first()

        if form and tenant:
            # Generate the form link
            form_link_url, form_link_expires_at = await create_form_link_for_template(
                session=session,
                form_id=form_id,
                contact_id=contact_id,
                is_single_use=template.form_link_single_use,
                expires_days=template.form_link_expires_days,
                base_url=base_url,
                tenant_slug=tenant.slug,
                form_slug=form.slug,
            )

            # Get the form link record to store the ID
            from app.services import form_links as form_links_service
            # The link was just created, get it by the token in the URL
            token = form_link_url.split("?t=")[-1] if "?t=" in form_link_url else None
            if token:
                link = await form_links_service.get_link_by_token(session, token)
                if link:
                    form_link_id = link.id

    # Load custom fields for the contact
    custom_fields = {}
    if contact.custom_fields:
        custom_fields = contact.custom_fields

    # Build the template context
    context = TemplateContext(
        contact=contact,
        form=form,
        form_link_url=form_link_url,
        form_link_expires_at=form_link_expires_at,
        message=message,
        tenant=tenant,
        custom_fields=custom_fields,
        extra=extra_context or {},
    )

    # Render the template
    rendered_subject, rendered_html, rendered_text = render_subject_and_body(
        subject=template.subject,
        body_html=template.body_html,
        body_text=template.body_text,
        context=context,
        strict=False,  # Replace undefined variables with empty string
    )

    # Update template usage stats
    template.send_count += 1
    template.last_sent_at = datetime.utcnow()

    # Send the email
    sent_email = await send_email(
        session=session,
        tenant_id=template.tenant_id,
        to_email=contact.email,
        to_name=contact.name,
        subject=rendered_subject,
        body_html=rendered_html,
        body_text=rendered_text,
        contact_id=contact_id,
        template_id=template_id,
        triggered_by=triggered_by,
        workflow_id=workflow_id,
        workflow_execution_id=workflow_execution_id,
        message_id=message_id,
        form_submission_id=form_submission_id,
        form_link_id=form_link_id,
    )

    return sent_email


def _decrypt_config(config: dict, provider: str) -> dict:
    """Decrypt sensitive configuration fields.

    This is a placeholder - implement actual decryption using your preferred method.
    Options include:
    - AWS KMS
    - Azure Key Vault
    - HashiCorp Vault
    - Application-level encryption with Fernet

    For now, we assume fields ending in '_encrypted' contain encrypted values
    and their decrypted counterparts should be stored without that suffix.
    """
    decrypted = {}

    for key, value in config.items():
        if key.endswith("_encrypted"):
            # In production, decrypt the value here
            # decrypted_value = decrypt(value)
            decrypted_key = key.replace("_encrypted", "")
            decrypted[decrypted_key] = value  # Placeholder: use raw value
        else:
            decrypted[key] = value

    return decrypted
