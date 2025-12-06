"""Campaign email sending service."""

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign, CampaignRecipient
from app.models.email import EmailTemplate, TenantEmailConfig, SentEmail
from app.models.contact import Contact
from app.models.tenant import Tenant
from app.services.email.providers import (
    EmailMessage,
    get_email_provider,
)
from app.services.email.template_renderer import (
    TemplateContext,
    render_subject_and_body,
)
from app.api.v1.email_webhooks import generate_tracking_token

logger = logging.getLogger(__name__)


class CampaignSendError(Exception):
    """Exception raised when campaign email sending fails."""

    def __init__(self, message: str, is_retryable: bool = True):
        self.message = message
        self.is_retryable = is_retryable
        super().__init__(message)


class CampaignSenderService:
    """Service for sending campaign emails with tracking."""

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        email_config: TenantEmailConfig,
        tracking_base_url: str | None = None,
    ):
        """Initialize the campaign sender.

        Args:
            session: Database session
            tenant_id: Tenant ID
            email_config: Email configuration for the tenant
            tracking_base_url: Base URL for tracking pixels and links
        """
        self.session = session
        self.tenant_id = tenant_id
        self.email_config = email_config
        self.tracking_base_url = tracking_base_url or ""

    async def send_campaign_email(
        self,
        campaign: Campaign,
        recipient: CampaignRecipient,
        contact: Contact | None,
        template: EmailTemplate,
    ) -> SentEmail:
        """Send a single campaign email with tracking.

        Args:
            campaign: The campaign being sent
            recipient: The recipient record
            contact: The contact (for template variables)
            template: The email template to use

        Returns:
            SentEmail record with tracking info
        """
        # Check rate limiting
        now = datetime.utcnow()
        if self.email_config.hour_window_start:
            hours_elapsed = (now - self.email_config.hour_window_start).total_seconds() / 3600
            if hours_elapsed >= 1:
                self.email_config.sends_this_hour = 0
                self.email_config.hour_window_start = now
        else:
            self.email_config.hour_window_start = now

        # Check campaign-specific rate limit or tenant default
        rate_limit = campaign.send_rate_per_hour or self.email_config.max_sends_per_hour
        if self.email_config.sends_this_hour >= rate_limit:
            raise CampaignSendError(
                f"Rate limit exceeded ({rate_limit}/hour)",
                is_retryable=True,
            )

        # Load tenant for context
        tenant_result = await self.session.execute(
            select(Tenant).where(Tenant.id == self.tenant_id)
        )
        tenant = tenant_result.scalars().first()

        # Build template context
        custom_fields = {}
        if contact and contact.custom_fields:
            custom_fields = contact.custom_fields

        context = TemplateContext(
            contact=contact,
            form=None,  # Campaigns don't typically include form links
            form_link_url=None,
            form_link_expires_at=None,
            message=None,
            tenant=tenant,
            custom_fields=custom_fields,
            extra={
                "campaign_name": campaign.name,
            },
        )

        # Render template
        rendered_subject, rendered_html, rendered_text = render_subject_and_body(
            subject=template.subject,
            body_html=template.body_html,
            body_text=template.body_text,
            context=context,
            strict=False,
        )

        # Create sent email record (pending)
        sent_email = SentEmail(
            tenant_id=self.tenant_id,
            template_id=template.id,
            to_email=recipient.email,
            to_name=contact.name if contact else None,
            contact_id=recipient.contact_id,
            subject=rendered_subject,
            body_html=rendered_html,
            body_text=rendered_text,
            triggered_by="campaign",
            status="pending",
        )
        self.session.add(sent_email)
        await self.session.flush()  # Get the sent_email.id

        # Add tracking pixel for opens
        if self.tracking_base_url:
            tracking_token = generate_tracking_token(str(sent_email.id), "open")
            tracking_pixel = (
                f'<img src="{self.tracking_base_url}/tracking/open/{tracking_token}" '
                f'width="1" height="1" style="display:none" alt="">'
            )
            rendered_html = rendered_html + tracking_pixel

            # Rewrite links for click tracking
            rendered_html = self._add_click_tracking(
                rendered_html, str(sent_email.id)
            )

        # Add unsubscribe header/link
        # TODO: Add List-Unsubscribe header

        # Decrypt config
        decrypted_config = self._decrypt_config(
            self.email_config.config, self.email_config.provider
        )

        try:
            # Get provider
            provider = get_email_provider(
                provider_type=self.email_config.provider,
                config=decrypted_config,
                from_email=campaign.from_email_override or self.email_config.from_email,
                from_name=campaign.from_name_override or self.email_config.from_name,
            )

            # Build message
            message = EmailMessage(
                to_email=recipient.email,
                to_name=contact.name if contact else None,
                subject=rendered_subject,
                body_html=rendered_html,
                body_text=rendered_text,
                reply_to=campaign.reply_to_override or self.email_config.reply_to_email,
            )

            # Send
            result = await provider.send(message)

            if result.success:
                sent_email.status = "sent"
                sent_email.sent_at = datetime.utcnow()
                sent_email.provider_message_id = result.message_id

                # Update rate limit counter
                self.email_config.sends_this_hour += 1
                self.email_config.last_send_at = now
                self.email_config.last_error = None

                # Update template stats
                template.send_count += 1
                template.last_sent_at = now
            else:
                sent_email.status = "failed"
                sent_email.error_message = result.error
                self.email_config.last_error = result.error
                logger.error(f"Failed to send campaign email: {result.error}")
                raise CampaignSendError(result.error or "Unknown error")

        except CampaignSendError:
            raise
        except Exception as e:
            sent_email.status = "failed"
            sent_email.error_message = str(e)
            self.email_config.last_error = str(e)
            logger.exception(f"Error sending campaign email: {e}")
            raise CampaignSendError(str(e))

        return sent_email

    def _add_click_tracking(self, html: str, sent_email_id: str) -> str:
        """Rewrite links to add click tracking.

        This is a simplified implementation. In production, you'd want to use
        a proper HTML parser (like BeautifulSoup) to handle edge cases.
        """
        import re

        if not self.tracking_base_url:
            return html

        def replace_link(match):
            url = match.group(1)
            # Skip tracking/unsubscribe links and mailto:
            if (
                "tracking/" in url
                or "unsubscribe" in url
                or url.startswith("mailto:")
                or url.startswith("#")
            ):
                return match.group(0)

            tracking_token = generate_tracking_token(sent_email_id, "click")
            encoded_url = url.replace("&", "%26")  # Basic URL encoding
            tracked_url = (
                f"{self.tracking_base_url}/tracking/click/{tracking_token}"
                f"?url={encoded_url}"
            )
            return f'href="{tracked_url}"'

        # Replace href attributes
        pattern = r'href="([^"]+)"'
        return re.sub(pattern, replace_link, html)

    def _decrypt_config(self, config: dict, provider: str) -> dict:
        """Decrypt sensitive configuration fields.

        See email/sender.py for full implementation notes.
        """
        decrypted = {}
        for key, value in config.items():
            if key.endswith("_encrypted"):
                decrypted_key = key.replace("_encrypted", "")
                decrypted[decrypted_key] = value  # Placeholder
            else:
                decrypted[key] = value
        return decrypted
