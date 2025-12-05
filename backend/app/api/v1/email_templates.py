"""Email template management endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func

from app.core.database import get_session
from app.api.v1.deps import PermissionChecker
from app.models.user import User, Permissions
from app.models.email import (
    EmailTemplate,
    EmailTemplateCreate,
    EmailTemplateRead,
    EmailTemplateUpdate,
    TenantEmailConfig,
    TenantEmailConfigCreate,
    TenantEmailConfigRead,
    TenantEmailConfigUpdate,
    SentEmail,
    SentEmailRead,
    TEMPLATE_VARIABLES,
)
from app.services.email.template_renderer import (
    validate_template,
    extract_template_variables,
    TemplateContext,
    render_template,
)

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================


class EmailTemplateListResponse(BaseModel):
    """Response for listing email templates."""

    items: list[EmailTemplateRead]
    total: int


class SentEmailListResponse(BaseModel):
    """Response for listing sent emails."""

    items: list[SentEmailRead]
    total: int
    page: int
    page_size: int


class TemplateVariablesResponse(BaseModel):
    """Response with available template variables."""

    variables: dict


class TemplateValidationResponse(BaseModel):
    """Response for template validation."""

    is_valid: bool
    error: str | None
    variables_used: list[str]


class TemplatePreviewRequest(BaseModel):
    """Request for previewing a template."""

    subject: str
    body_html: str
    body_text: str | None = None
    # Sample data for preview
    contact_name: str | None = "John Doe"
    contact_email: str | None = "john@example.com"
    form_name: str | None = "Feedback Survey"
    form_link_url: str | None = "https://app.example.com/f/demo/survey?t=abc123"


class TemplatePreviewResponse(BaseModel):
    """Response for template preview."""

    subject: str
    body_html: str
    body_text: str | None


class EmailConfigTestRequest(BaseModel):
    """Request to test email configuration."""

    test_email: str


class EmailConfigTestResponse(BaseModel):
    """Response from email config test."""

    success: bool
    message: str


# =============================================================================
# Email Template Endpoints
# =============================================================================


@router.get("/templates", response_model=EmailTemplateListResponse)
async def list_templates(
    is_active: bool | None = Query(None),
    current_user: User = Depends(PermissionChecker(Permissions.FORMS_READ)),
    session: AsyncSession = Depends(get_session),
) -> EmailTemplateListResponse:
    """List all email templates for the current tenant."""
    query = select(EmailTemplate).where(
        EmailTemplate.tenant_id == current_user.tenant_id
    )

    if is_active is not None:
        query = query.where(EmailTemplate.is_active == is_active)

    query = query.order_by(EmailTemplate.name)

    result = await session.execute(query)
    templates = result.scalars().all()

    return EmailTemplateListResponse(
        items=[EmailTemplateRead.model_validate(t) for t in templates],
        total=len(templates),
    )


@router.get("/templates/variables", response_model=TemplateVariablesResponse)
async def get_template_variables(
    current_user: User = Depends(PermissionChecker(Permissions.FORMS_READ)),
) -> TemplateVariablesResponse:
    """Get available template variables for documentation."""
    return TemplateVariablesResponse(variables=TEMPLATE_VARIABLES)


@router.get("/templates/{template_id}", response_model=EmailTemplateRead)
async def get_template(
    template_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.FORMS_READ)),
    session: AsyncSession = Depends(get_session),
) -> EmailTemplateRead:
    """Get a specific email template."""
    result = await session.execute(
        select(EmailTemplate).where(
            EmailTemplate.id == template_id,
            EmailTemplate.tenant_id == current_user.tenant_id,
        )
    )
    template = result.scalars().first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    return EmailTemplateRead.model_validate(template)


@router.post("/templates", response_model=EmailTemplateRead, status_code=status.HTTP_201_CREATED)
async def create_template(
    request: EmailTemplateCreate,
    current_user: User = Depends(PermissionChecker(Permissions.FORMS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> EmailTemplateRead:
    """Create a new email template."""
    # Validate the template syntax
    is_valid, error = validate_template(request.body_html)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid template syntax: {error}",
        )

    is_valid, error = validate_template(request.subject)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid subject template syntax: {error}",
        )

    template = EmailTemplate(
        tenant_id=current_user.tenant_id,
        name=request.name,
        description=request.description,
        subject=request.subject,
        body_html=request.body_html,
        body_text=request.body_text,
        design_json=request.design_json,
        default_form_id=request.default_form_id,
        form_link_single_use=request.form_link_single_use,
        form_link_expires_days=request.form_link_expires_days,
        attachments=request.attachments or [],
        is_active=request.is_active,
        send_count=0,
    )

    session.add(template)
    await session.commit()
    await session.refresh(template)

    return EmailTemplateRead.model_validate(template)


@router.patch("/templates/{template_id}", response_model=EmailTemplateRead)
async def update_template(
    template_id: UUID,
    request: EmailTemplateUpdate,
    current_user: User = Depends(PermissionChecker(Permissions.FORMS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> EmailTemplateRead:
    """Update an email template."""
    result = await session.execute(
        select(EmailTemplate).where(
            EmailTemplate.id == template_id,
            EmailTemplate.tenant_id == current_user.tenant_id,
        )
    )
    template = result.scalars().first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    # Validate template syntax if updating content
    if request.body_html:
        is_valid, error = validate_template(request.body_html)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid template syntax: {error}",
            )

    if request.subject:
        is_valid, error = validate_template(request.subject)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid subject template syntax: {error}",
            )

    # Apply updates
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    await session.commit()
    await session.refresh(template)

    return EmailTemplateRead.model_validate(template)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.FORMS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete an email template."""
    result = await session.execute(
        select(EmailTemplate).where(
            EmailTemplate.id == template_id,
            EmailTemplate.tenant_id == current_user.tenant_id,
        )
    )
    template = result.scalars().first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    await session.delete(template)
    await session.commit()


@router.post("/templates/{template_id}/duplicate", response_model=EmailTemplateRead)
async def duplicate_template(
    template_id: UUID,
    new_name: str = Query(..., min_length=1),
    current_user: User = Depends(PermissionChecker(Permissions.FORMS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> EmailTemplateRead:
    """Duplicate an email template."""
    result = await session.execute(
        select(EmailTemplate).where(
            EmailTemplate.id == template_id,
            EmailTemplate.tenant_id == current_user.tenant_id,
        )
    )
    original = result.scalars().first()

    if not original:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    new_template = EmailTemplate(
        tenant_id=current_user.tenant_id,
        name=new_name,
        description=original.description,
        subject=original.subject,
        body_html=original.body_html,
        body_text=original.body_text,
        design_json=original.design_json,
        default_form_id=original.default_form_id,
        form_link_single_use=original.form_link_single_use,
        form_link_expires_days=original.form_link_expires_days,
        attachments=original.attachments,
        is_active=False,  # Start as inactive
        send_count=0,
    )

    session.add(new_template)
    await session.commit()
    await session.refresh(new_template)

    return EmailTemplateRead.model_validate(new_template)


@router.post("/templates/validate", response_model=TemplateValidationResponse)
async def validate_template_content(
    subject: str = "",
    body_html: str = "",
    current_user: User = Depends(PermissionChecker(Permissions.FORMS_READ)),
) -> TemplateValidationResponse:
    """Validate template syntax and extract variables."""
    # Combine subject and body for full validation
    full_template = f"{subject}\n{body_html}"

    is_valid, error = validate_template(full_template)
    variables = extract_template_variables(full_template) if is_valid else []

    return TemplateValidationResponse(
        is_valid=is_valid,
        error=error,
        variables_used=variables,
    )


@router.post("/templates/preview", response_model=TemplatePreviewResponse)
async def preview_template(
    request: TemplatePreviewRequest,
    current_user: User = Depends(PermissionChecker(Permissions.FORMS_READ)),
) -> TemplatePreviewResponse:
    """Preview a template with sample data."""
    from app.models.contact import Contact
    from app.models.form import Form

    # Create mock objects for preview
    mock_contact = Contact(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        tenant_id=current_user.tenant_id,
        email=request.contact_email or "john@example.com",
        name=request.contact_name or "John Doe",
        message_count=0,
        tags=[],
    )

    mock_form = Form(
        id=UUID("00000000-0000-0000-0000-000000000002"),
        tenant_id=current_user.tenant_id,
        name=request.form_name or "Survey",
        slug="survey",
        status="published",
    )

    context = TemplateContext(
        contact=mock_contact,
        form=mock_form,
        form_link_url=request.form_link_url or "https://example.com/f/demo/survey?t=preview123",
        form_link_expires_at=None,
        tenant=None,
        message=None,
    )

    rendered_subject = render_template(request.subject, context, strict=False)
    rendered_html = render_template(request.body_html, context, strict=False)
    rendered_text = render_template(request.body_text, context, strict=False) if request.body_text else None

    return TemplatePreviewResponse(
        subject=rendered_subject,
        body_html=rendered_html,
        body_text=rendered_text,
    )


# =============================================================================
# Tenant Email Configuration Endpoints
# =============================================================================


@router.get("/config", response_model=TenantEmailConfigRead | None)
async def get_email_config(
    current_user: User = Depends(PermissionChecker(Permissions.SETTINGS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> TenantEmailConfigRead | None:
    """Get email configuration for the current tenant."""
    result = await session.execute(
        select(TenantEmailConfig).where(
            TenantEmailConfig.tenant_id == current_user.tenant_id
        )
    )
    config = result.scalars().first()

    if not config:
        return None

    return TenantEmailConfigRead.model_validate(config)


@router.post("/config", response_model=TenantEmailConfigRead, status_code=status.HTTP_201_CREATED)
async def create_email_config(
    request: TenantEmailConfigCreate,
    current_user: User = Depends(PermissionChecker(Permissions.SETTINGS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> TenantEmailConfigRead:
    """Create or replace email configuration for the current tenant."""
    # Check if config already exists
    result = await session.execute(
        select(TenantEmailConfig).where(
            TenantEmailConfig.tenant_id == current_user.tenant_id
        )
    )
    existing = result.scalars().first()

    if existing:
        # Update existing config
        existing.provider = request.provider
        existing.from_email = request.from_email
        existing.from_name = request.from_name
        existing.reply_to_email = request.reply_to_email
        existing.config = request.config
        existing.max_sends_per_hour = request.max_sends_per_hour
        existing.is_active = request.is_active
        config = existing
    else:
        # Create new config
        config = TenantEmailConfig(
            tenant_id=current_user.tenant_id,
            provider=request.provider,
            from_email=request.from_email,
            from_name=request.from_name,
            reply_to_email=request.reply_to_email,
            config=request.config,
            max_sends_per_hour=request.max_sends_per_hour,
            is_active=request.is_active,
            sends_this_hour=0,
        )
        session.add(config)

    await session.commit()
    await session.refresh(config)

    return TenantEmailConfigRead.model_validate(config)


@router.patch("/config", response_model=TenantEmailConfigRead)
async def update_email_config(
    request: TenantEmailConfigUpdate,
    current_user: User = Depends(PermissionChecker(Permissions.SETTINGS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> TenantEmailConfigRead:
    """Update email configuration for the current tenant."""
    result = await session.execute(
        select(TenantEmailConfig).where(
            TenantEmailConfig.tenant_id == current_user.tenant_id
        )
    )
    config = result.scalars().first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email configuration not found. Create one first.",
        )

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)

    await session.commit()
    await session.refresh(config)

    return TenantEmailConfigRead.model_validate(config)


@router.post("/config/test", response_model=EmailConfigTestResponse)
async def test_email_config(
    request: EmailConfigTestRequest,
    current_user: User = Depends(PermissionChecker(Permissions.SETTINGS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> EmailConfigTestResponse:
    """Test email configuration by sending a test email."""
    from app.services.email.providers import get_email_provider, EmailMessage

    result = await session.execute(
        select(TenantEmailConfig).where(
            TenantEmailConfig.tenant_id == current_user.tenant_id
        )
    )
    config = result.scalars().first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email configuration not found.",
        )

    try:
        # Create provider (without decryption for now - placeholder)
        provider = get_email_provider(
            provider_type=config.provider,
            config=config.config,  # In production, decrypt sensitive fields
            from_email=config.from_email,
            from_name=config.from_name,
        )

        # Validate configuration
        is_valid, error = await provider.validate_config()
        if not is_valid:
            return EmailConfigTestResponse(
                success=False,
                message=f"Configuration validation failed: {error}",
            )

        # Send test email
        test_message = EmailMessage(
            to_email=request.test_email,
            to_name=None,
            subject="Dewey Email Configuration Test",
            body_html="""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2>Email Configuration Test</h2>
                <p>If you're reading this, your email configuration is working correctly.</p>
                <p style="color: #666;">
                    Sent from Dewey at {time}
                </p>
            </body>
            </html>
            """.format(time=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")),
            body_text="Email Configuration Test\n\nIf you're reading this, your email configuration is working correctly.",
        )

        result = await provider.send(test_message)

        if result.success:
            return EmailConfigTestResponse(
                success=True,
                message=f"Test email sent successfully to {request.test_email}",
            )
        else:
            return EmailConfigTestResponse(
                success=False,
                message=f"Failed to send test email: {result.error}",
            )

    except Exception as e:
        return EmailConfigTestResponse(
            success=False,
            message=f"Error: {str(e)}",
        )


# =============================================================================
# Sent Email Log Endpoints
# =============================================================================


@router.get("/sent", response_model=SentEmailListResponse)
async def list_sent_emails(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    template_id: UUID | None = Query(None),
    contact_id: UUID | None = Query(None),
    current_user: User = Depends(PermissionChecker(Permissions.FORMS_READ)),
    session: AsyncSession = Depends(get_session),
) -> SentEmailListResponse:
    """List sent emails for the current tenant."""
    query = select(SentEmail).where(
        SentEmail.tenant_id == current_user.tenant_id
    )

    if status_filter:
        query = query.where(SentEmail.status == status_filter)
    if template_id:
        query = query.where(SentEmail.template_id == template_id)
    if contact_id:
        query = query.where(SentEmail.contact_id == contact_id)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and ordering
    offset = (page - 1) * page_size
    query = query.order_by(SentEmail.created_at.desc()).offset(offset).limit(page_size)

    result = await session.execute(query)
    emails = result.scalars().all()

    return SentEmailListResponse(
        items=[SentEmailRead.model_validate(e) for e in emails],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/sent/{email_id}", response_model=SentEmailRead)
async def get_sent_email(
    email_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.FORMS_READ)),
    session: AsyncSession = Depends(get_session),
) -> SentEmailRead:
    """Get details of a sent email."""
    result = await session.execute(
        select(SentEmail).where(
            SentEmail.id == email_id,
            SentEmail.tenant_id == current_user.tenant_id,
        )
    )
    email = result.scalars().first()

    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found",
        )

    return SentEmailRead.model_validate(email)
