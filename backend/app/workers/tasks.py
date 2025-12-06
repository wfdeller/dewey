"""ARQ task definitions for background job processing."""

from datetime import datetime
from uuid import UUID

import structlog
from sqlmodel import select

from app.core.database import async_session_maker
from app.models.job import Job
from app.services.voter_import import VoterImportService


logger = structlog.get_logger()


async def _mark_job_failed(job_id: str, tenant_id: str, error_message: str) -> None:
    """Mark a job as failed in the database.

    Uses a separate session to ensure the failure is recorded even if
    the main session was rolled back.
    """
    try:
        async with async_session_maker() as session:
            result = await session.execute(
                select(Job).where(
                    Job.id == UUID(job_id),
                    Job.tenant_id == UUID(tenant_id),
                )
            )
            job = result.scalars().first()
            if job:
                job.status = "failed"
                job.error_message = error_message[:1000]  # Truncate long errors
                job.completed_at = datetime.utcnow()
                await session.commit()
                logger.info("Marked job as failed", job_id=job_id)
    except Exception as e:
        logger.error("Failed to mark job as failed", job_id=job_id, error=str(e))


async def process_voter_import(ctx: dict, job_id: str, tenant_id: str) -> dict:
    """ARQ task for processing voter file import.

    Args:
        ctx: ARQ context (contains job info, redis connection)
        job_id: The Job UUID as string
        tenant_id: The tenant UUID as string

    Returns:
        Result dictionary with status and job_id
    """
    logger.info(
        "Starting voter import task",
        job_id=job_id,
        tenant_id=tenant_id,
        arq_job_id=ctx.get("job_id"),
    )

    try:
        async with async_session_maker() as session:
            service = VoterImportService(session, UUID(tenant_id))
            await service.process_import(UUID(job_id))

        logger.info(
            "Completed voter import task",
            job_id=job_id,
            tenant_id=tenant_id,
        )

        return {"status": "completed", "job_id": job_id}

    except Exception as e:
        error_msg = str(e)
        logger.error(
            "Voter import task failed",
            job_id=job_id,
            tenant_id=tenant_id,
            error=error_msg,
        )
        # Mark the job as failed in a separate session
        await _mark_job_failed(job_id, tenant_id, error_msg)
        # Don't re-raise - job is marked as failed, no point in ARQ retrying
        return {"status": "failed", "job_id": job_id, "error": error_msg}


async def export_contacts(
    ctx: dict, job_id: str, tenant_id: str, filters: dict | None = None
) -> dict:
    """ARQ task for exporting contacts.

    Args:
        ctx: ARQ context
        job_id: The Job UUID as string
        tenant_id: The tenant UUID as string
        filters: Optional filter criteria for contacts

    Returns:
        Result dictionary with status and job_id

    TODO: Implement contact export functionality
    """
    logger.info(
        "Contact export task placeholder",
        job_id=job_id,
        tenant_id=tenant_id,
        filters=filters,
    )
    return {"status": "not_implemented", "job_id": job_id}


async def send_campaign_emails(
    ctx: dict, job_id: str, tenant_id: str, campaign_id: str
) -> dict:
    """ARQ task for sending campaign emails.

    Processes campaign recipients in batches, rendering templates and
    sending emails while respecting rate limits and handling pause/cancel.

    Args:
        ctx: ARQ context
        job_id: The Job UUID as string
        tenant_id: The tenant UUID as string
        campaign_id: The campaign UUID as string

    Returns:
        Result dictionary with status, counts, and job_id
    """
    from app.models.campaign import Campaign, CampaignRecipient
    from app.models.email import EmailTemplate, TenantEmailConfig, SentEmail, EmailSuppression
    from app.models.contact import Contact
    from app.services.campaign_sender import CampaignSenderService

    logger.info(
        "Starting campaign send task",
        job_id=job_id,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
    )

    sent_count = 0
    failed_count = 0
    skipped_count = 0

    try:
        async with async_session_maker() as session:
            # Load campaign and verify status
            result = await session.execute(
                select(Campaign).where(
                    Campaign.id == UUID(campaign_id),
                    Campaign.tenant_id == UUID(tenant_id),
                )
            )
            campaign = result.scalars().first()

            if not campaign:
                raise ValueError(f"Campaign {campaign_id} not found")

            if campaign.status not in ("active", "paused"):
                logger.warning(
                    "Campaign not in sendable state",
                    campaign_id=campaign_id,
                    status=campaign.status,
                )
                return {
                    "status": "skipped",
                    "job_id": job_id,
                    "reason": f"Campaign status is {campaign.status}",
                }

            # Check if paused - exit early
            if campaign.status == "paused":
                logger.info("Campaign is paused, exiting", campaign_id=campaign_id)
                return {
                    "status": "paused",
                    "job_id": job_id,
                    "sent": sent_count,
                }

            # Load email template
            template_result = await session.execute(
                select(EmailTemplate).where(EmailTemplate.id == campaign.template_id)
            )
            template = template_result.scalars().first()

            if not template:
                raise ValueError(f"Template {campaign.template_id} not found")

            # Load variant B template if A/B testing
            variant_b_template = None
            if campaign.variant_b_template_id:
                variant_b_result = await session.execute(
                    select(EmailTemplate).where(
                        EmailTemplate.id == campaign.variant_b_template_id
                    )
                )
                variant_b_template = variant_b_result.scalars().first()

            # Load tenant email config
            config_result = await session.execute(
                select(TenantEmailConfig).where(
                    TenantEmailConfig.tenant_id == UUID(tenant_id),
                    TenantEmailConfig.is_active == True,  # noqa: E712
                )
            )
            email_config = config_result.scalars().first()

            if not email_config:
                raise ValueError("No active email configuration found for tenant")

            # Initialize sender service
            sender_service = CampaignSenderService(
                session=session,
                tenant_id=UUID(tenant_id),
                email_config=email_config,
            )

            # Process pending recipients in batches
            batch_size = 100
            processed_in_batch = 0

            while True:
                # Check campaign status (may have been paused/cancelled)
                await session.refresh(campaign)
                if campaign.status == "paused":
                    logger.info("Campaign paused mid-send", campaign_id=campaign_id)
                    break
                if campaign.status == "cancelled":
                    logger.info("Campaign cancelled mid-send", campaign_id=campaign_id)
                    break

                # Get batch of pending recipients
                recipients_result = await session.execute(
                    select(CampaignRecipient)
                    .where(
                        CampaignRecipient.campaign_id == UUID(campaign_id),
                        CampaignRecipient.status == "pending",
                    )
                    .limit(batch_size)
                )
                recipients = recipients_result.scalars().all()

                if not recipients:
                    # No more pending recipients
                    break

                for recipient in recipients:
                    try:
                        # Check suppression
                        suppressed = await session.execute(
                            select(EmailSuppression).where(
                                EmailSuppression.tenant_id == UUID(tenant_id),
                                EmailSuppression.email == recipient.email.lower(),
                                EmailSuppression.is_active == True,  # noqa: E712
                            )
                        )
                        if suppressed.scalars().first():
                            recipient.status = "failed"
                            recipient.error_message = "Email is suppressed"
                            skipped_count += 1
                            continue

                        # Get contact for template rendering
                        contact_result = await session.execute(
                            select(Contact).where(Contact.id == recipient.contact_id)
                        )
                        contact = contact_result.scalars().first()

                        # Determine which template to use (A/B testing)
                        use_template = template
                        if recipient.variant == "b" and variant_b_template:
                            use_template = variant_b_template

                        # Mark as queued
                        recipient.status = "queued"
                        recipient.queued_at = datetime.utcnow()
                        await session.flush()

                        # Send email
                        sent_email = await sender_service.send_campaign_email(
                            campaign=campaign,
                            recipient=recipient,
                            contact=contact,
                            template=use_template,
                        )

                        # Update recipient with sent email reference
                        recipient.sent_email_id = sent_email.id
                        recipient.status = "sent"
                        recipient.sent_at = datetime.utcnow()
                        sent_count += 1

                        # Update campaign stats
                        campaign.total_sent += 1

                    except Exception as e:
                        logger.error(
                            "Failed to send to recipient",
                            recipient_id=str(recipient.id),
                            email=recipient.email,
                            error=str(e),
                        )
                        recipient.status = "failed"
                        recipient.failed_at = datetime.utcnow()
                        recipient.error_message = str(e)[:500]
                        failed_count += 1
                        campaign.total_failed += 1

                # Commit batch
                await session.commit()
                processed_in_batch += len(recipients)

                logger.info(
                    "Processed batch",
                    campaign_id=campaign_id,
                    batch_sent=len(recipients),
                    total_sent=sent_count,
                )

            # Check if campaign is complete
            remaining_result = await session.execute(
                select(CampaignRecipient)
                .where(
                    CampaignRecipient.campaign_id == UUID(campaign_id),
                    CampaignRecipient.status == "pending",
                )
                .limit(1)
            )
            if not remaining_result.scalars().first() and campaign.status == "active":
                campaign.status = "completed"
                campaign.completed_at = datetime.utcnow()

            # Update job status
            job_result = await session.execute(
                select(Job).where(Job.id == UUID(job_id))
            )
            job = job_result.scalars().first()
            if job:
                job.status = "completed" if campaign.status == "completed" else "paused"
                job.completed_at = datetime.utcnow()
                job.result = {
                    "sent": sent_count,
                    "failed": failed_count,
                    "skipped": skipped_count,
                }

            await session.commit()

        logger.info(
            "Campaign send task finished",
            job_id=job_id,
            campaign_id=campaign_id,
            sent=sent_count,
            failed=failed_count,
            skipped=skipped_count,
            final_status=campaign.status,
        )

        return {
            "status": "completed",
            "job_id": job_id,
            "campaign_id": campaign_id,
            "sent": sent_count,
            "failed": failed_count,
            "skipped": skipped_count,
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(
            "Campaign send task failed",
            job_id=job_id,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            error=error_msg,
        )
        await _mark_job_failed(job_id, tenant_id, error_msg)
        return {
            "status": "failed",
            "job_id": job_id,
            "error": error_msg,
            "sent": sent_count,
        }


async def generate_campaign_recommendations(ctx: dict, tenant_id: str) -> dict:
    """ARQ task to generate campaign recommendations based on message trends.

    Analyzes message categories and trends to suggest outbound campaigns.

    Args:
        ctx: ARQ context
        tenant_id: The tenant UUID as string

    Returns:
        Result dictionary with generated recommendation count
    """
    from datetime import timedelta
    from sqlalchemy import func as sql_func
    from app.models.campaign_recommendation import CampaignRecommendation
    from app.models.category import Category, MessageCategory
    from app.models.message import Message
    from app.models.contact import Contact

    logger.info("Starting campaign recommendation generation", tenant_id=tenant_id)

    recommendations_created = 0

    try:
        async with async_session_maker() as session:
            # Get message counts by category for last 30 days vs previous 30 days
            now = datetime.utcnow()
            thirty_days_ago = now - timedelta(days=30)
            sixty_days_ago = now - timedelta(days=60)

            # Get categories with recent activity
            categories_result = await session.execute(
                select(Category).where(Category.tenant_id == UUID(tenant_id))
            )
            categories = categories_result.scalars().all()

            for category in categories:
                # Count messages in current period
                current_count_result = await session.execute(
                    select(sql_func.count(MessageCategory.message_id))
                    .where(
                        MessageCategory.category_id == category.id,
                    )
                    .join(Message)
                    .where(
                        Message.received_at >= thirty_days_ago,
                        Message.tenant_id == UUID(tenant_id),
                    )
                )
                current_count = current_count_result.scalar() or 0

                # Count messages in previous period
                previous_count_result = await session.execute(
                    select(sql_func.count(MessageCategory.message_id))
                    .where(MessageCategory.category_id == category.id)
                    .join(Message)
                    .where(
                        Message.received_at >= sixty_days_ago,
                        Message.received_at < thirty_days_ago,
                        Message.tenant_id == UUID(tenant_id),
                    )
                )
                previous_count = previous_count_result.scalar() or 0

                # Check for significant increase (>25%)
                if previous_count > 0:
                    change_percent = ((current_count - previous_count) / previous_count) * 100
                elif current_count > 10:  # New trending topic
                    change_percent = 100
                else:
                    continue

                if change_percent < 25 or current_count < 5:
                    continue

                # Check if we already have an active recommendation for this category
                existing = await session.execute(
                    select(CampaignRecommendation).where(
                        CampaignRecommendation.tenant_id == UUID(tenant_id),
                        CampaignRecommendation.category_id == category.id,
                        CampaignRecommendation.status == "active",
                    )
                )
                if existing.scalars().first():
                    continue

                # Get sample message IDs
                sample_messages_result = await session.execute(
                    select(Message.id)
                    .join(MessageCategory)
                    .where(
                        MessageCategory.category_id == category.id,
                        Message.tenant_id == UUID(tenant_id),
                        Message.received_at >= thirty_days_ago,
                    )
                    .limit(5)
                )
                sample_ids = [str(row[0]) for row in sample_messages_result.all()]

                # Estimate audience size (contacts who sent messages about this category)
                audience_result = await session.execute(
                    select(sql_func.count(sql_func.distinct(Message.contact_id)))
                    .join(MessageCategory)
                    .where(
                        MessageCategory.category_id == category.id,
                        Message.tenant_id == UUID(tenant_id),
                        Message.contact_id.isnot(None),
                    )
                )
                audience_size = audience_result.scalar() or 0

                # Create recommendation
                recommendation = CampaignRecommendation(
                    tenant_id=UUID(tenant_id),
                    trigger_type="trending_topic",
                    category_id=category.id,
                    topic_keywords=[category.name],
                    trend_data={
                        "period": "30_days",
                        "current_count": current_count,
                        "previous_count": previous_count,
                        "change_percent": round(change_percent, 1),
                        "sample_message_ids": sample_ids,
                    },
                    title=f"Interest in '{category.name}' is up {int(change_percent)}%",
                    description=(
                        f"There has been a {int(change_percent)}% increase in messages "
                        f"about {category.name} over the past 30 days. "
                        f"Consider reaching out to engaged contacts."
                    ),
                    suggested_audience_size=audience_size,
                    suggested_filter={
                        "mode": "filter",
                        "categories": [{"id": str(category.id)}],
                        "category_match": "any",
                        "exclude_suppressed": True,
                    },
                    confidence_score=min(0.9, 0.5 + (change_percent / 200)),
                    status="active",
                    expires_at=now + timedelta(days=14),
                )
                session.add(recommendation)
                recommendations_created += 1

            await session.commit()

        logger.info(
            "Campaign recommendation generation complete",
            tenant_id=tenant_id,
            created=recommendations_created,
        )

        return {
            "status": "completed",
            "tenant_id": tenant_id,
            "recommendations_created": recommendations_created,
        }

    except Exception as e:
        logger.error(
            "Campaign recommendation generation failed",
            tenant_id=tenant_id,
            error=str(e),
        )
        return {"status": "failed", "error": str(e)}


async def check_scheduled_campaigns(ctx: dict) -> dict:
    """ARQ cron task to start campaigns that are due to be sent.

    Runs periodically to check for campaigns with scheduled_at <= now
    and starts them.

    Args:
        ctx: ARQ context

    Returns:
        Result dictionary with started campaign count
    """
    from app.models.campaign import Campaign

    logger.info("Checking for scheduled campaigns")

    started_count = 0

    try:
        async with async_session_maker() as session:
            now = datetime.utcnow()

            # Find campaigns ready to start
            result = await session.execute(
                select(Campaign).where(
                    Campaign.status == "scheduled",
                    Campaign.scheduled_at <= now,
                )
            )
            campaigns = result.scalars().all()

            for campaign in campaigns:
                logger.info(
                    "Starting scheduled campaign",
                    campaign_id=str(campaign.id),
                    tenant_id=str(campaign.tenant_id),
                )

                campaign.status = "active"
                campaign.started_at = now

                # Create job
                job = Job(
                    tenant_id=campaign.tenant_id,
                    job_type="campaign_send",
                    status="pending",
                    parameters={"campaign_id": str(campaign.id)},
                )
                session.add(job)
                await session.flush()

                campaign.job_id = job.id
                started_count += 1

                # Note: In production, enqueue the send task here
                # await arq_redis.enqueue_job(
                #     "send_campaign_emails",
                #     job_id=str(job.id),
                #     tenant_id=str(campaign.tenant_id),
                #     campaign_id=str(campaign.id),
                # )

            await session.commit()

        logger.info("Scheduled campaign check complete", started=started_count)
        return {"status": "completed", "started": started_count}

    except Exception as e:
        logger.error("Scheduled campaign check failed", error=str(e))
        return {"status": "failed", "error": str(e)}
