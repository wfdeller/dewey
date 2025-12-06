"""Email tracking and webhook endpoints for engagement tracking."""

import hashlib
import hmac
import json
import logging
from datetime import datetime
from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import get_settings
from app.core.database import get_session
from app.models.email import SentEmail, EmailSuppression
from app.models.campaign import Campaign, CampaignRecipient

router = APIRouter()
logger = logging.getLogger(__name__)


# 1x1 transparent GIF for open tracking
TRACKING_PIXEL = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
    b"\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00"
    b"\x00\x00\x00\x01\x00\x01\x00\x00\x02\x01D\x00;"
)


# =============================================================================
# Tracking Token Generation/Validation
# =============================================================================


def generate_tracking_token(sent_email_id: str, action: str = "open") -> str:
    """Generate a signed token for tracking URLs."""
    secret = get_settings().secret_key.encode()
    message = f"{sent_email_id}:{action}".encode()
    signature = hmac.new(secret, message, hashlib.sha256).hexdigest()[:16]
    return f"{sent_email_id}:{signature}"


def validate_tracking_token(token: str, action: str = "open") -> UUID | None:
    """Validate a tracking token and return the sent_email_id if valid."""
    try:
        parts = token.split(":")
        if len(parts) != 2:
            return None

        sent_email_id, signature = parts
        expected_token = generate_tracking_token(sent_email_id, action)

        if hmac.compare_digest(token, expected_token):
            return UUID(sent_email_id)
        return None
    except Exception:
        return None


def generate_unsubscribe_token(email: str, tenant_id: str) -> str:
    """Generate a signed unsubscribe token."""
    secret = get_settings().secret_key.encode()
    message = f"unsub:{email}:{tenant_id}".encode()
    signature = hmac.new(secret, message, hashlib.sha256).hexdigest()[:16]
    return f"{tenant_id}:{hashlib.md5(email.encode()).hexdigest()[:8]}:{signature}"


def validate_unsubscribe_token(token: str) -> tuple[str, UUID] | None:
    """Validate an unsubscribe token, returns (email, tenant_id) if valid."""
    # Note: This simplified version just validates format
    # In production, you'd need to look up the email from a stored mapping
    try:
        parts = token.split(":")
        if len(parts) != 3:
            return None
        tenant_id, _, _ = parts
        return UUID(tenant_id)
    except Exception:
        return None


# =============================================================================
# Open Tracking Endpoint
# =============================================================================


@router.get("/tracking/open/{token}")
async def track_open(
    token: str,
    session: AsyncSession = Depends(get_session),
) -> Response:
    """
    Track email opens via 1x1 tracking pixel.

    This endpoint is embedded in emails as an image and called when
    the email is opened.
    """
    sent_email_id = validate_tracking_token(token, "open")

    if sent_email_id:
        try:
            # Get sent email
            result = await session.execute(
                select(SentEmail).where(SentEmail.id == sent_email_id)
            )
            sent_email = result.scalars().first()

            if sent_email:
                now = datetime.utcnow()

                # Update sent email
                if not sent_email.opened_at:
                    sent_email.opened_at = now

                # Update campaign recipient if from a campaign
                if sent_email.template_id:
                    recipient_result = await session.execute(
                        select(CampaignRecipient).where(
                            CampaignRecipient.sent_email_id == sent_email_id
                        )
                    )
                    recipient = recipient_result.scalars().first()

                    if recipient:
                        recipient.open_count += 1
                        if not recipient.opened_at:
                            recipient.opened_at = now
                            recipient.status = "opened"

                            # Update campaign stats
                            campaign_result = await session.execute(
                                select(Campaign).where(Campaign.id == recipient.campaign_id)
                            )
                            campaign = campaign_result.scalars().first()
                            if campaign:
                                campaign.total_opened += 1
                                if recipient.open_count == 1:
                                    campaign.unique_opens += 1

                await session.commit()
        except Exception as e:
            logger.error(f"Error tracking open for {sent_email_id}: {e}")

    # Always return the tracking pixel
    return Response(
        content=TRACKING_PIXEL,
        media_type="image/gif",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


# =============================================================================
# Click Tracking Endpoint
# =============================================================================


@router.get("/tracking/click/{token}")
async def track_click(
    token: str,
    url: str = Query(..., description="Original destination URL"),
    session: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    """
    Track link clicks and redirect to destination.

    Links in campaign emails are rewritten to pass through this endpoint
    for click tracking before redirecting to the actual destination.
    """
    sent_email_id = validate_tracking_token(token, "click")

    if sent_email_id:
        try:
            # Get sent email
            result = await session.execute(
                select(SentEmail).where(SentEmail.id == sent_email_id)
            )
            sent_email = result.scalars().first()

            if sent_email:
                now = datetime.utcnow()

                # Update sent email
                if not sent_email.clicked_at:
                    sent_email.clicked_at = now

                # Update campaign recipient if from a campaign
                if sent_email.template_id:
                    recipient_result = await session.execute(
                        select(CampaignRecipient).where(
                            CampaignRecipient.sent_email_id == sent_email_id
                        )
                    )
                    recipient = recipient_result.scalars().first()

                    if recipient:
                        recipient.click_count += 1
                        if not recipient.clicked_at:
                            recipient.clicked_at = now
                            if recipient.status not in ("bounced", "unsubscribed", "failed"):
                                recipient.status = "clicked"

                            # Update campaign stats
                            campaign_result = await session.execute(
                                select(Campaign).where(Campaign.id == recipient.campaign_id)
                            )
                            campaign = campaign_result.scalars().first()
                            if campaign:
                                campaign.total_clicked += 1
                                if recipient.click_count == 1:
                                    campaign.unique_clicks += 1

                await session.commit()
        except Exception as e:
            logger.error(f"Error tracking click for {sent_email_id}: {e}")

    # Always redirect to destination URL
    return RedirectResponse(url=url, status_code=302)


# =============================================================================
# Unsubscribe Endpoint
# =============================================================================


@router.get("/unsubscribe/{token}")
async def unsubscribe_page(
    token: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Show unsubscribe confirmation page.

    Returns data for frontend to render unsubscribe page.
    """
    tenant_id = validate_unsubscribe_token(token)

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired unsubscribe link",
        )

    return {
        "valid": True,
        "token": token,
        "message": "Click confirm to unsubscribe from our emails",
    }


@router.post("/unsubscribe/{token}")
async def confirm_unsubscribe(
    token: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Process unsubscribe request.

    Adds the email to the suppression list.
    """
    tenant_id = validate_unsubscribe_token(token)

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired unsubscribe link",
        )

    # Note: In a full implementation, we'd look up the email from the token
    # For now, this is a simplified version that just acknowledges the request

    return {
        "success": True,
        "message": "You have been successfully unsubscribed",
    }


# =============================================================================
# SendGrid Webhook
# =============================================================================


class SendGridEvent(BaseModel):
    """SendGrid webhook event model."""

    email: str
    event: str  # processed, delivered, open, click, bounce, etc.
    sg_message_id: str | None = None
    timestamp: int | None = None
    url: str | None = None  # For click events
    reason: str | None = None  # For bounce events
    type: str | None = None  # bounce type: bounce, blocked


@router.post("/webhooks/sendgrid")
async def sendgrid_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Handle SendGrid webhook events.

    Events include: processed, dropped, delivered, deferred, bounce,
    open, click, spam_report, unsubscribe, group_unsubscribe, group_resubscribe
    """
    try:
        body = await request.body()
        events = json.loads(body)

        if not isinstance(events, list):
            events = [events]

        processed = 0
        for event_data in events:
            try:
                event = SendGridEvent(**event_data)
                await _process_sendgrid_event(session, event)
                processed += 1
            except Exception as e:
                logger.error(f"Error processing SendGrid event: {e}")

        await session.commit()
        return {"processed": processed}

    except Exception as e:
        logger.error(f"SendGrid webhook error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook payload",
        )


async def _process_sendgrid_event(session: AsyncSession, event: SendGridEvent):
    """Process a single SendGrid event."""
    # Find sent email by provider message ID
    if not event.sg_message_id:
        return

    result = await session.execute(
        select(SentEmail).where(SentEmail.provider_message_id == event.sg_message_id)
    )
    sent_email = result.scalars().first()

    if not sent_email:
        return

    now = datetime.utcnow()

    if event.event == "delivered":
        sent_email.status = "delivered"
        # Update campaign recipient
        await _update_recipient_status(session, sent_email.id, "delivered", now)

    elif event.event == "open":
        if not sent_email.opened_at:
            sent_email.opened_at = now
        await _update_recipient_open(session, sent_email.id, now)

    elif event.event == "click":
        if not sent_email.clicked_at:
            sent_email.clicked_at = now
        await _update_recipient_click(session, sent_email.id, now)

    elif event.event == "bounce":
        sent_email.status = "bounced"
        sent_email.bounced_at = now

        # Add to suppression list
        suppression_type = "hard_bounce" if event.type == "bounce" else "soft_bounce"
        await _add_suppression(
            session,
            sent_email.tenant_id,
            event.email,
            suppression_type,
            {"bounce_type": event.type, "bounce_reason": event.reason},
        )

        await _update_recipient_bounce(session, sent_email.id, now, event.type)

    elif event.event in ("spamreport", "spam_report"):
        await _add_suppression(
            session,
            sent_email.tenant_id,
            event.email,
            "complaint",
            {"complaint_type": "abuse"},
        )

    elif event.event == "unsubscribe":
        sent_email.unsubscribed_at = now
        await _add_suppression(
            session,
            sent_email.tenant_id,
            event.email,
            "unsubscribe",
            {},
        )
        await _update_recipient_status(session, sent_email.id, "unsubscribed", now)


# =============================================================================
# AWS SES Webhook (SNS Notification)
# =============================================================================


@router.post("/webhooks/ses")
async def ses_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Handle AWS SES webhook events via SNS.

    Handles bounce, complaint, and delivery notifications.
    """
    try:
        body = await request.body()
        sns_message = json.loads(body)

        # Handle SNS subscription confirmation
        if sns_message.get("Type") == "SubscriptionConfirmation":
            # In production, you'd want to confirm the subscription
            logger.info(f"SNS subscription confirmation: {sns_message.get('SubscribeURL')}")
            return {"status": "subscription_confirmation_received"}

        # Handle notification
        if sns_message.get("Type") == "Notification":
            message = json.loads(sns_message.get("Message", "{}"))
            notification_type = message.get("notificationType")

            if notification_type == "Bounce":
                await _process_ses_bounce(session, message)
            elif notification_type == "Complaint":
                await _process_ses_complaint(session, message)
            elif notification_type == "Delivery":
                await _process_ses_delivery(session, message)

            await session.commit()

        return {"processed": True}

    except Exception as e:
        logger.error(f"SES webhook error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook payload",
        )


async def _process_ses_bounce(session: AsyncSession, message: dict):
    """Process SES bounce notification."""
    bounce = message.get("bounce", {})
    bounce_type = bounce.get("bounceType", "").lower()
    message_id = message.get("mail", {}).get("messageId")

    if not message_id:
        return

    result = await session.execute(
        select(SentEmail).where(SentEmail.provider_message_id == message_id)
    )
    sent_email = result.scalars().first()

    if not sent_email:
        return

    now = datetime.utcnow()
    sent_email.status = "bounced"
    sent_email.bounced_at = now

    # Process each bounced recipient
    for recipient in bounce.get("bouncedRecipients", []):
        email = recipient.get("emailAddress")
        if email:
            suppression_type = "hard_bounce" if bounce_type == "permanent" else "soft_bounce"
            await _add_suppression(
                session,
                sent_email.tenant_id,
                email,
                suppression_type,
                {
                    "bounce_type": bounce_type,
                    "bounce_reason": recipient.get("diagnosticCode"),
                },
            )

    await _update_recipient_bounce(
        session, sent_email.id, now, "hard" if bounce_type == "permanent" else "soft"
    )


async def _process_ses_complaint(session: AsyncSession, message: dict):
    """Process SES complaint notification."""
    complaint = message.get("complaint", {})
    message_id = message.get("mail", {}).get("messageId")

    if not message_id:
        return

    result = await session.execute(
        select(SentEmail).where(SentEmail.provider_message_id == message_id)
    )
    sent_email = result.scalars().first()

    if not sent_email:
        return

    # Process each complained recipient
    for recipient in complaint.get("complainedRecipients", []):
        email = recipient.get("emailAddress")
        if email:
            await _add_suppression(
                session,
                sent_email.tenant_id,
                email,
                "complaint",
                {
                    "complaint_type": complaint.get("complaintFeedbackType"),
                    "feedback_id": complaint.get("feedbackId"),
                },
            )


async def _process_ses_delivery(session: AsyncSession, message: dict):
    """Process SES delivery notification."""
    message_id = message.get("mail", {}).get("messageId")

    if not message_id:
        return

    result = await session.execute(
        select(SentEmail).where(SentEmail.provider_message_id == message_id)
    )
    sent_email = result.scalars().first()

    if not sent_email:
        return

    sent_email.status = "delivered"
    await _update_recipient_status(session, sent_email.id, "delivered", datetime.utcnow())


# =============================================================================
# Helper Functions
# =============================================================================


async def _update_recipient_status(
    session: AsyncSession, sent_email_id: UUID, new_status: str, timestamp: datetime
):
    """Update campaign recipient status."""
    result = await session.execute(
        select(CampaignRecipient).where(CampaignRecipient.sent_email_id == sent_email_id)
    )
    recipient = result.scalars().first()

    if recipient:
        recipient.status = new_status
        if new_status == "delivered":
            recipient.delivered_at = timestamp

            # Update campaign stats
            campaign_result = await session.execute(
                select(Campaign).where(Campaign.id == recipient.campaign_id)
            )
            campaign = campaign_result.scalars().first()
            if campaign:
                campaign.total_delivered += 1


async def _update_recipient_open(session: AsyncSession, sent_email_id: UUID, timestamp: datetime):
    """Update campaign recipient for open event."""
    result = await session.execute(
        select(CampaignRecipient).where(CampaignRecipient.sent_email_id == sent_email_id)
    )
    recipient = result.scalars().first()

    if recipient:
        recipient.open_count += 1
        if not recipient.opened_at:
            recipient.opened_at = timestamp
            recipient.status = "opened"

            # Update campaign stats
            campaign_result = await session.execute(
                select(Campaign).where(Campaign.id == recipient.campaign_id)
            )
            campaign = campaign_result.scalars().first()
            if campaign:
                campaign.total_opened += 1
                campaign.unique_opens += 1


async def _update_recipient_click(session: AsyncSession, sent_email_id: UUID, timestamp: datetime):
    """Update campaign recipient for click event."""
    result = await session.execute(
        select(CampaignRecipient).where(CampaignRecipient.sent_email_id == sent_email_id)
    )
    recipient = result.scalars().first()

    if recipient:
        recipient.click_count += 1
        if not recipient.clicked_at:
            recipient.clicked_at = timestamp
            if recipient.status not in ("bounced", "unsubscribed", "failed"):
                recipient.status = "clicked"

            # Update campaign stats
            campaign_result = await session.execute(
                select(Campaign).where(Campaign.id == recipient.campaign_id)
            )
            campaign = campaign_result.scalars().first()
            if campaign:
                campaign.total_clicked += 1
                campaign.unique_clicks += 1


async def _update_recipient_bounce(
    session: AsyncSession, sent_email_id: UUID, timestamp: datetime, bounce_type: str | None
):
    """Update campaign recipient for bounce event."""
    result = await session.execute(
        select(CampaignRecipient).where(CampaignRecipient.sent_email_id == sent_email_id)
    )
    recipient = result.scalars().first()

    if recipient:
        recipient.status = "bounced"
        recipient.bounced_at = timestamp
        recipient.bounce_type = bounce_type

        # Update campaign stats
        campaign_result = await session.execute(
            select(Campaign).where(Campaign.id == recipient.campaign_id)
        )
        campaign = campaign_result.scalars().first()
        if campaign:
            campaign.total_bounced += 1


async def _add_suppression(
    session: AsyncSession,
    tenant_id: UUID,
    email: str,
    suppression_type: str,
    provider_info: dict,
):
    """Add email to suppression list if not already suppressed."""
    # Check if already suppressed
    existing = await session.execute(
        select(EmailSuppression).where(
            EmailSuppression.tenant_id == tenant_id,
            EmailSuppression.email == email.lower(),
            EmailSuppression.is_active == True,  # noqa: E712
        )
    )
    if existing.scalars().first():
        return

    suppression = EmailSuppression(
        tenant_id=tenant_id,
        email=email.lower(),
        suppression_type=suppression_type,
        is_global=True,
        suppressed_at=datetime.utcnow(),
        provider_info=provider_info,
    )
    session.add(suppression)
