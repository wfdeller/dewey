"""Form builder and submission endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func

from app.core.database import get_session
from app.api.v1.deps import PermissionChecker
from app.models.user import User, Permissions
from app.models.form import (
    Form,
    FormCreate,
    FormRead,
    FormField,
    FormFieldCreate,
    FormFieldRead,
    FormSubmission,
    FormSubmissionCreate,
    FormSubmissionRead,
    FormStatus,
)

router = APIRouter()


class FormListResponse(BaseModel):
    """Form list response."""

    items: list[FormRead]
    total: int


class FormDetailResponse(FormRead):
    """Form with fields."""

    fields: list[FormFieldRead] = []


class FormUpdate(BaseModel):
    """Schema for updating a form."""

    name: str | None = None
    description: str | None = None
    slug: str | None = None
    status: FormStatus | None = None
    settings: dict | None = None
    styling: dict | None = None


class FormFieldUpdate(BaseModel):
    """Schema for updating a form field."""

    label: str | None = None
    placeholder: str | None = None
    help_text: str | None = None
    is_required: bool | None = None
    sort_order: int | None = None
    validation: dict | None = None
    options: list[dict] | None = None
    conditional_logic: dict | None = None
    settings: dict | None = None


class FormSubmissionListResponse(BaseModel):
    """Paginated form submission list response."""

    items: list[FormSubmissionRead]
    total: int
    page: int
    page_size: int
    pages: int


class FormAnalyticsResponse(BaseModel):
    """Form analytics summary."""

    form_id: UUID
    total_submissions: int
    submissions_today: int
    submissions_this_week: int
    completion_rate: float | None
    avg_completion_time_seconds: float | None


# =============================================================================
# Form Management Endpoints
# =============================================================================


@router.get("", response_model=FormListResponse)
async def list_forms(
    status_filter: FormStatus | None = Query(None, alias="status"),
    current_user: User = Depends(PermissionChecker(Permissions.FORMS_READ)),
    session: AsyncSession = Depends(get_session),
) -> FormListResponse:
    """List all forms for the current tenant."""
    query = select(Form).where(Form.tenant_id == current_user.tenant_id)

    if status_filter:
        query = query.where(Form.status == status_filter)

    query = query.order_by(Form.updated_at.desc())

    result = await session.execute(query)
    forms = result.scalars().all()

    return FormListResponse(
        items=[FormRead.model_validate(f) for f in forms],
        total=len(forms),
    )


@router.get("/{form_id}", response_model=FormDetailResponse)
async def get_form(
    form_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.FORMS_READ)),
    session: AsyncSession = Depends(get_session),
) -> FormDetailResponse:
    """Get a form with all its fields."""
    result = await session.execute(
        select(Form).where(
            Form.id == form_id,
            Form.tenant_id == current_user.tenant_id,
        )
    )
    form = result.scalars().first()

    if not form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form not found",
        )

    # Get fields
    fields_result = await session.execute(
        select(FormField)
        .where(FormField.form_id == form_id)
        .order_by(FormField.sort_order)
    )
    fields = fields_result.scalars().all()

    return FormDetailResponse(
        **FormRead.model_validate(form).model_dump(),
        fields=[FormFieldRead.model_validate(f) for f in fields],
    )


@router.post("", response_model=FormRead, status_code=status.HTTP_201_CREATED)
async def create_form(
    request: FormCreate,
    current_user: User = Depends(PermissionChecker(Permissions.FORMS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> FormRead:
    """Create a new form."""
    # Check for duplicate slug within tenant
    result = await session.execute(
        select(Form).where(
            Form.tenant_id == current_user.tenant_id,
            Form.slug == request.slug,
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Form with this slug already exists",
        )

    form = Form(
        tenant_id=current_user.tenant_id,
        **request.model_dump(),
    )
    session.add(form)
    await session.commit()
    await session.refresh(form)

    return FormRead.model_validate(form)


@router.patch("/{form_id}", response_model=FormRead)
async def update_form(
    form_id: UUID,
    request: FormUpdate,
    current_user: User = Depends(PermissionChecker(Permissions.FORMS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> FormRead:
    """Update a form's properties."""
    result = await session.execute(
        select(Form).where(
            Form.id == form_id,
            Form.tenant_id == current_user.tenant_id,
        )
    )
    form = result.scalars().first()

    if not form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form not found",
        )

    # Check slug uniqueness if changing
    if request.slug and request.slug != form.slug:
        slug_result = await session.execute(
            select(Form).where(
                Form.tenant_id == current_user.tenant_id,
                Form.slug == request.slug,
                Form.id != form_id,
            )
        )
        if slug_result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Form with this slug already exists",
            )

    # Apply updates
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(form, field, value)

    await session.commit()
    await session.refresh(form)

    return FormRead.model_validate(form)


@router.delete("/{form_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_form(
    form_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.FORMS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a form and all its fields and submissions."""
    result = await session.execute(
        select(Form).where(
            Form.id == form_id,
            Form.tenant_id == current_user.tenant_id,
        )
    )
    form = result.scalars().first()

    if not form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form not found",
        )

    # Delete is cascaded via relationships
    await session.delete(form)
    await session.commit()


@router.post("/{form_id}/duplicate", response_model=FormRead)
async def duplicate_form(
    form_id: UUID,
    new_name: str = Query(..., min_length=1),
    new_slug: str = Query(..., min_length=1),
    current_user: User = Depends(PermissionChecker(Permissions.FORMS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> FormRead:
    """Duplicate a form with its fields."""
    result = await session.execute(
        select(Form).where(
            Form.id == form_id,
            Form.tenant_id == current_user.tenant_id,
        )
    )
    original = result.scalars().first()

    if not original:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form not found",
        )

    # Check slug uniqueness
    slug_result = await session.execute(
        select(Form).where(
            Form.tenant_id == current_user.tenant_id,
            Form.slug == new_slug,
        )
    )
    if slug_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Form with this slug already exists",
        )

    # Create new form
    new_form = Form(
        tenant_id=current_user.tenant_id,
        name=new_name,
        slug=new_slug,
        description=original.description,
        status="draft",
        settings=original.settings,
        styling=original.styling,
    )
    session.add(new_form)
    await session.flush()

    # Duplicate fields
    fields_result = await session.execute(
        select(FormField).where(FormField.form_id == form_id)
    )
    for field in fields_result.scalars().all():
        new_field = FormField(
            form_id=new_form.id,
            field_type=field.field_type,
            label=field.label,
            placeholder=field.placeholder,
            help_text=field.help_text,
            is_required=field.is_required,
            sort_order=field.sort_order,
            validation=field.validation,
            options=field.options,
            conditional_logic=field.conditional_logic,
            maps_to_contact_field=field.maps_to_contact_field,
            maps_to_custom_field_id=field.maps_to_custom_field_id,
            settings=field.settings,
        )
        session.add(new_field)

    await session.commit()
    await session.refresh(new_form)

    return FormRead.model_validate(new_form)


# =============================================================================
# Form Field Endpoints
# =============================================================================


@router.post("/{form_id}/fields", response_model=FormFieldRead, status_code=status.HTTP_201_CREATED)
async def add_form_field(
    form_id: UUID,
    request: FormFieldCreate,
    current_user: User = Depends(PermissionChecker(Permissions.FORMS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> FormFieldRead:
    """Add a field to a form."""
    # Verify form exists and belongs to tenant
    form_result = await session.execute(
        select(Form).where(
            Form.id == form_id,
            Form.tenant_id == current_user.tenant_id,
        )
    )
    if not form_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form not found",
        )

    field = FormField(
        form_id=form_id,
        **request.model_dump(),
    )
    session.add(field)
    await session.commit()
    await session.refresh(field)

    return FormFieldRead.model_validate(field)


@router.patch("/{form_id}/fields/{field_id}", response_model=FormFieldRead)
async def update_form_field(
    form_id: UUID,
    field_id: UUID,
    request: FormFieldUpdate,
    current_user: User = Depends(PermissionChecker(Permissions.FORMS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> FormFieldRead:
    """Update a form field."""
    # Verify form exists and belongs to tenant
    form_result = await session.execute(
        select(Form).where(
            Form.id == form_id,
            Form.tenant_id == current_user.tenant_id,
        )
    )
    if not form_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form not found",
        )

    # Get field
    result = await session.execute(
        select(FormField).where(
            FormField.id == field_id,
            FormField.form_id == form_id,
        )
    )
    field = result.scalars().first()

    if not field:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Field not found",
        )

    # Apply updates
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(field, key, value)

    await session.commit()
    await session.refresh(field)

    return FormFieldRead.model_validate(field)


@router.delete("/{form_id}/fields/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_form_field(
    form_id: UUID,
    field_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.FORMS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a form field."""
    # Verify form exists and belongs to tenant
    form_result = await session.execute(
        select(Form).where(
            Form.id == form_id,
            Form.tenant_id == current_user.tenant_id,
        )
    )
    if not form_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form not found",
        )

    # Get field
    result = await session.execute(
        select(FormField).where(
            FormField.id == field_id,
            FormField.form_id == form_id,
        )
    )
    field = result.scalars().first()

    if not field:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Field not found",
        )

    await session.delete(field)
    await session.commit()


@router.post("/{form_id}/fields/reorder", response_model=list[FormFieldRead])
async def reorder_form_fields(
    form_id: UUID,
    field_order: list[UUID],
    current_user: User = Depends(PermissionChecker(Permissions.FORMS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> list[FormFieldRead]:
    """Reorder form fields."""
    # Verify form exists and belongs to tenant
    form_result = await session.execute(
        select(Form).where(
            Form.id == form_id,
            Form.tenant_id == current_user.tenant_id,
        )
    )
    if not form_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form not found",
        )

    # Update sort_order for each field
    for index, fid in enumerate(field_order):
        result = await session.execute(
            select(FormField).where(
                FormField.id == fid,
                FormField.form_id == form_id,
            )
        )
        field = result.scalars().first()
        if field:
            field.sort_order = index

    await session.commit()

    # Return updated fields
    fields_result = await session.execute(
        select(FormField)
        .where(FormField.form_id == form_id)
        .order_by(FormField.sort_order)
    )
    fields = fields_result.scalars().all()

    return [FormFieldRead.model_validate(f) for f in fields]


# =============================================================================
# Form Submission Endpoints
# =============================================================================


@router.get("/{form_id}/submissions", response_model=FormSubmissionListResponse)
async def list_form_submissions(
    form_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    current_user: User = Depends(PermissionChecker(Permissions.FORMS_READ)),
    session: AsyncSession = Depends(get_session),
) -> FormSubmissionListResponse:
    """List submissions for a form."""
    # Verify form exists and belongs to tenant
    form_result = await session.execute(
        select(Form).where(
            Form.id == form_id,
            Form.tenant_id == current_user.tenant_id,
        )
    )
    if not form_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form not found",
        )

    query = (
        select(FormSubmission)
        .where(FormSubmission.form_id == form_id)
        .order_by(FormSubmission.submitted_at.desc())
    )

    if status_filter:
        query = query.where(FormSubmission.status == status_filter)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await session.execute(query)
    submissions = result.scalars().all()

    pages = (total + page_size - 1) // page_size

    return FormSubmissionListResponse(
        items=[FormSubmissionRead.model_validate(s) for s in submissions],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("/{form_id}/submit", response_model=FormSubmissionRead, status_code=status.HTTP_201_CREATED)
async def submit_form(
    form_id: UUID,
    request: FormSubmissionCreate,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
) -> FormSubmissionRead:
    """
    Submit a form response.

    This is a public endpoint - no authentication required for published forms.
    """
    # Get form (must be published)
    result = await session.execute(
        select(Form).where(
            Form.id == form_id,
            Form.status == "published",
        )
    )
    form = result.scalars().first()

    if not form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form not found or not published",
        )

    # TODO: Validate field_values against form fields
    # TODO: Check required fields
    # TODO: Run spam detection

    # Create submission
    submission = FormSubmission(
        form_id=form_id,
        field_values=request.field_values,
        ip_address=request.ip_address or (http_request.client.host if http_request.client else None),
        user_agent=request.user_agent or http_request.headers.get("user-agent"),
        referrer_url=request.referrer_url,
        utm_params=request.utm_params or {},
    )
    session.add(submission)
    await session.commit()
    await session.refresh(submission)

    # TODO: Queue for processing (create Message, link Contact, etc.)

    return FormSubmissionRead.model_validate(submission)


@router.get("/{form_id}/analytics", response_model=FormAnalyticsResponse)
async def get_form_analytics(
    form_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.ANALYTICS_READ)),
    session: AsyncSession = Depends(get_session),
) -> FormAnalyticsResponse:
    """Get analytics for a form."""
    # Verify form exists and belongs to tenant
    form_result = await session.execute(
        select(Form).where(
            Form.id == form_id,
            Form.tenant_id == current_user.tenant_id,
        )
    )
    if not form_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form not found",
        )

    # Get total submissions
    total_result = await session.execute(
        select(func.count()).where(FormSubmission.form_id == form_id)
    )
    total = total_result.scalar() or 0

    # TODO: Calculate today/week counts and completion metrics

    return FormAnalyticsResponse(
        form_id=form_id,
        total_submissions=total,
        submissions_today=0,  # TODO
        submissions_this_week=0,  # TODO
        completion_rate=None,  # TODO
        avg_completion_time_seconds=None,  # TODO
    )


# =============================================================================
# Public Form Endpoints (for embedding)
# =============================================================================


@router.get("/public/{tenant_slug}/{form_slug}", response_model=FormDetailResponse)
async def get_public_form(
    tenant_slug: str,
    form_slug: str,
    session: AsyncSession = Depends(get_session),
) -> FormDetailResponse:
    """
    Get a public form by tenant and form slug.

    Used by embedded forms and direct links.
    Only returns published forms.
    """
    # Import here to avoid circular imports
    from app.models.tenant import Tenant

    # Find tenant by slug
    tenant_result = await session.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = tenant_result.scalars().first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form not found",
        )

    # Find published form
    form_result = await session.execute(
        select(Form).where(
            Form.tenant_id == tenant.id,
            Form.slug == form_slug,
            Form.status == "published",
        )
    )
    form = form_result.scalars().first()

    if not form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form not found",
        )

    # Get fields
    fields_result = await session.execute(
        select(FormField)
        .where(FormField.form_id == form.id)
        .order_by(FormField.sort_order)
    )
    fields = fields_result.scalars().all()

    return FormDetailResponse(
        **FormRead.model_validate(form).model_dump(),
        fields=[FormFieldRead.model_validate(f) for f in fields],
    )
