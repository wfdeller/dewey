"""Workflow management endpoints."""

import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select, func

from app.core.database import get_session
from app.api.v1.deps import PermissionChecker
from app.models.user import User, Permissions
from app.models.workflow import (
    Workflow,
    WorkflowCreate,
    WorkflowRead,
    WorkflowUpdate,
    WorkflowExecution,
    WorkflowExecutionRead,
)
from app.models.message import Message
from app.models.analysis import Analysis
from app.models.category import MessageCategory

router = APIRouter()


class WorkflowListResponse(BaseModel):
    """Workflow list response."""

    items: list[WorkflowRead]
    total: int


class WorkflowExecutionListResponse(BaseModel):
    """Paginated workflow execution list response."""

    items: list[WorkflowExecutionRead]
    total: int
    page: int
    page_size: int
    pages: int


class WorkflowTestRequest(BaseModel):
    """Request to test a workflow against sample data."""

    message_id: UUID | None = None
    sample_data: dict | None = None


class WorkflowTestResult(BaseModel):
    """Result of workflow test."""

    would_trigger: bool
    matched_conditions: list[dict]
    unmatched_conditions: list[dict]
    actions_that_would_execute: list[dict]


class TriggerCondition(BaseModel):
    """Schema for a trigger condition."""

    field: str
    operator: str  # eq, ne, gt, lt, gte, lte, in, not_in, contains, starts_with
    value: str | int | float | list


class WorkflowTriggerSchema(BaseModel):
    """Schema for workflow trigger configuration."""

    conditions: list[TriggerCondition]
    match: str = "all"  # all or any


class WorkflowActionSchema(BaseModel):
    """Schema for a workflow action."""

    type: str  # auto_reply, assign, add_category, notify, webhook, update_field
    config: dict


class WorkflowStatsResponse(BaseModel):
    """Workflow execution statistics."""

    total_workflows: int
    active_workflows: int
    total_executions: int
    executions_today: int
    success_rate: float


# =============================================================================
# Workflow Endpoints
# =============================================================================


@router.get("", response_model=WorkflowListResponse)
async def list_workflows(
    include_inactive: bool = Query(False, description="Include inactive workflows"),
    current_user: User = Depends(PermissionChecker(Permissions.WORKFLOWS_READ)),
    session: AsyncSession = Depends(get_session),
) -> WorkflowListResponse:
    """List all workflows for the current tenant."""
    query = select(Workflow).where(Workflow.tenant_id == current_user.tenant_id)

    if not include_inactive:
        query = query.where(Workflow.is_active == True)

    query = query.order_by(Workflow.priority.desc(), Workflow.name)

    result = await session.execute(query)
    workflows = result.scalars().all()

    return WorkflowListResponse(
        items=[WorkflowRead.model_validate(w) for w in workflows],
        total=len(workflows),
    )


@router.get("/{workflow_id}", response_model=WorkflowRead)
async def get_workflow(
    workflow_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.WORKFLOWS_READ)),
    session: AsyncSession = Depends(get_session),
) -> WorkflowRead:
    """Get a specific workflow by ID."""
    result = await session.execute(
        select(Workflow).where(
            Workflow.id == workflow_id,
            Workflow.tenant_id == current_user.tenant_id,
        )
    )
    workflow = result.scalars().first()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    return WorkflowRead.model_validate(workflow)


@router.post("", response_model=WorkflowRead, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    request: WorkflowCreate,
    current_user: User = Depends(PermissionChecker(Permissions.WORKFLOWS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> WorkflowRead:
    """
    Create a new workflow.

    Workflows automate actions based on message attributes like sentiment,
    categories, keywords, sender, etc.
    """
    # Validate trigger structure
    if not request.trigger.get("conditions"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow trigger must have at least one condition",
        )

    # Validate actions
    if not request.actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow must have at least one action",
        )

    workflow = Workflow(
        tenant_id=current_user.tenant_id,
        **request.model_dump(),
    )
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)

    return WorkflowRead.model_validate(workflow)


@router.patch("/{workflow_id}", response_model=WorkflowRead)
async def update_workflow(
    workflow_id: UUID,
    request: WorkflowUpdate,
    current_user: User = Depends(PermissionChecker(Permissions.WORKFLOWS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> WorkflowRead:
    """Update a workflow."""
    result = await session.execute(
        select(Workflow).where(
            Workflow.id == workflow_id,
            Workflow.tenant_id == current_user.tenant_id,
        )
    )
    workflow = result.scalars().first()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    # Validate trigger if being updated
    if request.trigger is not None and not request.trigger.get("conditions"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow trigger must have at least one condition",
        )

    # Validate actions if being updated
    if request.actions is not None and not request.actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow must have at least one action",
        )

    # Apply updates
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(workflow, field, value)

    await session.commit()
    await session.refresh(workflow)

    return WorkflowRead.model_validate(workflow)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.WORKFLOWS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a workflow."""
    result = await session.execute(
        select(Workflow).where(
            Workflow.id == workflow_id,
            Workflow.tenant_id == current_user.tenant_id,
        )
    )
    workflow = result.scalars().first()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    await session.delete(workflow)
    await session.commit()


@router.post("/{workflow_id}/test", response_model=WorkflowTestResult)
async def test_workflow(
    workflow_id: UUID,
    request: WorkflowTestRequest,
    current_user: User = Depends(PermissionChecker(Permissions.WORKFLOWS_READ)),
    session: AsyncSession = Depends(get_session),
) -> WorkflowTestResult:
    """
    Test a workflow against a message or sample data.

    Returns whether the workflow would trigger and which actions would execute.
    Does not actually execute the workflow.
    """
    result = await session.execute(
        select(Workflow).where(
            Workflow.id == workflow_id,
            Workflow.tenant_id == current_user.tenant_id,
        )
    )
    workflow = result.scalars().first()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    # Build test data
    test_data = {}

    if request.message_id:
        # Load message with analysis
        msg_result = await session.execute(
            select(Message)
            .where(
                Message.id == request.message_id,
                Message.tenant_id == current_user.tenant_id,
            )
            .options(
                selectinload(Message.analysis),
                selectinload(Message.message_categories),
            )
        )
        message = msg_result.scalars().first()

        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found",
            )

        # Build test data from message
        test_data = {
            "source": message.source,
            "sender_email": message.sender_email,
            "subject": message.subject,
            "body_text": message.body_text,
            "is_template_match": message.is_template_match,
        }

        # Add analysis data if available
        if message.analysis:
            test_data["sentiment_score"] = message.analysis.sentiment_score
            test_data["sentiment_label"] = message.analysis.sentiment_label
            test_data["urgency_score"] = message.analysis.urgency_score

        # Add category IDs
        test_data["category_ids"] = [mc.category_id for mc in message.message_categories]

    elif request.sample_data:
        test_data = request.sample_data
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either message_id or sample_data is required",
        )

    # Evaluate trigger conditions
    matched_conditions = []
    unmatched_conditions = []
    trigger = workflow.trigger
    conditions = trigger.get("conditions", [])
    match_mode = trigger.get("match", "all")

    for condition in conditions:
        field = condition.get("field")
        operator = condition.get("operator")
        expected_value = condition.get("value")

        # Get actual value from test data
        if field == "category_id":
            actual_value = test_data.get("category_ids", [])
        else:
            actual_value = test_data.get(field)

        # Evaluate condition
        condition_met = _evaluate_condition(actual_value, operator, expected_value, field)

        condition_result = {
            **condition,
            "actual_value": actual_value,
            "matched": condition_met,
        }

        if condition_met:
            matched_conditions.append(condition_result)
        else:
            unmatched_conditions.append(condition_result)

    # Determine if workflow would trigger
    if match_mode == "all":
        would_trigger = len(unmatched_conditions) == 0 and len(matched_conditions) > 0
    else:  # "any"
        would_trigger = len(matched_conditions) > 0

    return WorkflowTestResult(
        would_trigger=would_trigger,
        matched_conditions=matched_conditions,
        unmatched_conditions=unmatched_conditions,
        actions_that_would_execute=workflow.actions if would_trigger else [],
    )


@router.post("/{workflow_id}/toggle", response_model=WorkflowRead)
async def toggle_workflow(
    workflow_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.WORKFLOWS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> WorkflowRead:
    """Toggle a workflow's active status."""
    result = await session.execute(
        select(Workflow).where(
            Workflow.id == workflow_id,
            Workflow.tenant_id == current_user.tenant_id,
        )
    )
    workflow = result.scalars().first()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    workflow.is_active = not workflow.is_active
    await session.commit()
    await session.refresh(workflow)

    return WorkflowRead.model_validate(workflow)


@router.get("/{workflow_id}/executions", response_model=WorkflowExecutionListResponse)
async def list_workflow_executions(
    workflow_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    current_user: User = Depends(PermissionChecker(Permissions.WORKFLOWS_READ)),
    session: AsyncSession = Depends(get_session),
) -> WorkflowExecutionListResponse:
    """Get execution history for a workflow."""
    # Verify workflow exists and belongs to tenant
    workflow_result = await session.execute(
        select(Workflow).where(
            Workflow.id == workflow_id,
            Workflow.tenant_id == current_user.tenant_id,
        )
    )
    if not workflow_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    query = (
        select(WorkflowExecution)
        .where(WorkflowExecution.workflow_id == workflow_id)
        .order_by(WorkflowExecution.triggered_at.desc())
    )

    if status_filter:
        query = query.where(WorkflowExecution.status == status_filter)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await session.execute(query)
    executions = result.scalars().all()

    pages = (total + page_size - 1) // page_size

    return WorkflowExecutionListResponse(
        items=[WorkflowExecutionRead.model_validate(e) for e in executions],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("/{workflow_id}/duplicate", response_model=WorkflowRead)
async def duplicate_workflow(
    workflow_id: UUID,
    current_user: User = Depends(PermissionChecker(Permissions.WORKFLOWS_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> WorkflowRead:
    """Create a copy of an existing workflow."""
    result = await session.execute(
        select(Workflow).where(
            Workflow.id == workflow_id,
            Workflow.tenant_id == current_user.tenant_id,
        )
    )
    workflow = result.scalars().first()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    # Create duplicate with modified name
    new_workflow = Workflow(
        tenant_id=current_user.tenant_id,
        name=f"{workflow.name} (Copy)",
        description=workflow.description,
        is_active=False,  # Start inactive
        priority=workflow.priority,
        trigger=workflow.trigger,
        actions=workflow.actions,
    )
    session.add(new_workflow)
    await session.commit()
    await session.refresh(new_workflow)

    return WorkflowRead.model_validate(new_workflow)


@router.get("/trigger-fields")
async def get_trigger_fields(
    current_user: User = Depends(PermissionChecker(Permissions.WORKFLOWS_READ)),
) -> dict:
    """
    Get available fields for workflow triggers.

    Returns metadata about fields that can be used in trigger conditions.
    """
    return {
        "fields": [
            {
                "key": "sentiment_score",
                "name": "Sentiment Score",
                "type": "number",
                "operators": ["eq", "ne", "gt", "lt", "gte", "lte"],
                "description": "AI-detected sentiment (-1 to 1)",
            },
            {
                "key": "sentiment_label",
                "name": "Sentiment Label",
                "type": "string",
                "operators": ["eq", "ne", "in"],
                "options": ["positive", "neutral", "negative"],
                "description": "Sentiment category",
            },
            {
                "key": "urgency_score",
                "name": "Urgency Score",
                "type": "number",
                "operators": ["eq", "ne", "gt", "lt", "gte", "lte"],
                "description": "AI-detected urgency (0 to 1)",
            },
            {
                "key": "category_id",
                "name": "Category",
                "type": "uuid",
                "operators": ["eq", "ne", "in", "not_in"],
                "description": "Assigned category",
            },
            {
                "key": "source",
                "name": "Message Source",
                "type": "string",
                "operators": ["eq", "ne", "in"],
                "options": ["email", "form", "api", "upload"],
                "description": "How the message was received",
            },
            {
                "key": "sender_email",
                "name": "Sender Email",
                "type": "string",
                "operators": ["eq", "ne", "contains", "starts_with", "ends_with"],
                "description": "Sender's email address",
            },
            {
                "key": "subject",
                "name": "Subject",
                "type": "string",
                "operators": ["contains", "starts_with", "regex"],
                "description": "Message subject line",
            },
            {
                "key": "body_text",
                "name": "Message Body",
                "type": "string",
                "operators": ["contains", "regex"],
                "description": "Message content",
            },
            {
                "key": "is_template_match",
                "name": "Is Campaign Message",
                "type": "boolean",
                "operators": ["eq"],
                "description": "Whether message is part of a detected campaign",
            },
        ]
    }


@router.get("/action-types")
async def get_action_types(
    current_user: User = Depends(PermissionChecker(Permissions.WORKFLOWS_READ)),
) -> dict:
    """
    Get available action types for workflows.

    Returns metadata about actions that can be configured.
    """
    return {
        "actions": [
            {
                "type": "auto_reply",
                "name": "Send Auto-Reply",
                "description": "Send an automated email response",
                "config_schema": {
                    "template_id": {"type": "uuid", "required": True},
                },
            },
            {
                "type": "assign",
                "name": "Assign to User",
                "description": "Assign the message to a specific user",
                "config_schema": {
                    "user_id": {"type": "uuid", "required": True},
                },
            },
            {
                "type": "add_category",
                "name": "Add Category",
                "description": "Automatically categorize the message",
                "config_schema": {
                    "category_id": {"type": "uuid", "required": True},
                },
            },
            {
                "type": "notify",
                "name": "Send Notification",
                "description": "Send a notification to users",
                "config_schema": {
                    "channel": {"type": "string", "enum": ["email", "slack"], "required": True},
                    "recipients": {"type": "array", "items": "string", "required": True},
                    "message": {"type": "string", "required": False},
                },
            },
            {
                "type": "webhook",
                "name": "Call Webhook",
                "description": "Send data to an external URL",
                "config_schema": {
                    "url": {"type": "string", "required": True},
                    "method": {"type": "string", "enum": ["POST", "PUT"], "default": "POST"},
                    "headers": {"type": "object", "required": False},
                },
            },
            {
                "type": "update_field",
                "name": "Update Custom Field",
                "description": "Update a contact's custom field value",
                "config_schema": {
                    "field_id": {"type": "uuid", "required": True},
                    "value": {"type": "any", "required": True},
                },
            },
        ]
    }


# =============================================================================
# Helper Functions
# =============================================================================


def _evaluate_condition(
    actual_value,
    operator: str,
    expected_value,
    field: str,
) -> bool:
    """Evaluate a single trigger condition."""
    try:
        # Handle null actual values
        if actual_value is None:
            return operator == "ne"

        # Comparison operators
        if operator == "eq":
            if field == "category_id" and isinstance(actual_value, list):
                # Check if expected category is in the list
                return str(expected_value) in [str(v) for v in actual_value]
            return actual_value == expected_value

        elif operator == "ne":
            if field == "category_id" and isinstance(actual_value, list):
                return str(expected_value) not in [str(v) for v in actual_value]
            return actual_value != expected_value

        elif operator == "gt":
            return float(actual_value) > float(expected_value)

        elif operator == "lt":
            return float(actual_value) < float(expected_value)

        elif operator == "gte":
            return float(actual_value) >= float(expected_value)

        elif operator == "lte":
            return float(actual_value) <= float(expected_value)

        elif operator == "in":
            if isinstance(expected_value, list):
                if field == "category_id" and isinstance(actual_value, list):
                    # Check if any expected category is in the list
                    return any(str(v) in [str(e) for e in expected_value] for v in actual_value)
                return actual_value in expected_value
            return str(actual_value) in str(expected_value)

        elif operator == "not_in":
            if isinstance(expected_value, list):
                if field == "category_id" and isinstance(actual_value, list):
                    return not any(str(v) in [str(e) for e in expected_value] for v in actual_value)
                return actual_value not in expected_value
            return str(actual_value) not in str(expected_value)

        elif operator == "contains":
            return str(expected_value).lower() in str(actual_value).lower()

        elif operator == "starts_with":
            return str(actual_value).lower().startswith(str(expected_value).lower())

        elif operator == "ends_with":
            return str(actual_value).lower().endswith(str(expected_value).lower())

        elif operator == "regex":
            try:
                return bool(re.search(str(expected_value), str(actual_value), re.IGNORECASE))
            except re.error:
                return False

        return False

    except (ValueError, TypeError):
        return False
