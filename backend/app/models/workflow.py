"""Workflow model for automation rules."""

from datetime import datetime
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.base import TenantBaseModel, BaseModel

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.message import Message


ExecutionStatus = Literal["running", "completed", "failed"]


class WorkflowBase(SQLModel):
    """Workflow base schema."""

    name: str = Field(index=True)
    description: str | None = Field(default=None, sa_column=Column(Text))
    is_active: bool = Field(default=True)
    priority: int = Field(default=0)  # Higher = runs first


class Workflow(WorkflowBase, TenantBaseModel, table=True):
    """Workflow database model for automation rules."""

    __tablename__ = "workflow"

    # Trigger conditions (evaluated in order)
    trigger: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    # Structure: {
    #   "conditions": [
    #     {"field": "sentiment_score", "operator": "lt", "value": -0.5},
    #     {"field": "category_id", "operator": "in", "value": ["uuid1", "uuid2"]},
    #     {"field": "keywords", "operator": "contains", "value": ["urgent", "help"]},
    #   ],
    #   "match": "all" | "any"
    # }

    # Actions to execute when triggered
    actions: list[dict] = Field(default_factory=list, sa_column=Column(JSONB))
    # Structure: [
    #   {"type": "auto_reply", "template_id": "uuid"},
    #   {"type": "assign", "user_id": "uuid"},
    #   {"type": "add_category", "category_id": "uuid"},
    #   {"type": "notify", "channel": "email|slack", "recipients": ["..."]},
    #   {"type": "webhook", "url": "...", "method": "POST"},
    #   {"type": "update_field", "field": "...", "value": "..."},
    # ]

    # Relationships
    tenant: "Tenant" = Relationship(back_populates="workflows")
    executions: list["WorkflowExecution"] = Relationship(back_populates="workflow")


class WorkflowExecution(BaseModel, table=True):
    """Audit log for workflow executions."""

    __tablename__ = "workflow_execution"

    workflow_id: UUID = Field(foreign_key="workflow.id", index=True)
    message_id: UUID = Field(foreign_key="message.id", index=True)

    # Execution tracking
    triggered_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    completed_at: datetime | None = None
    status: str = Field(default="running")  # running, completed, failed

    # Details of what happened
    actions_executed: list[dict] = Field(default_factory=list, sa_column=Column(JSONB))
    # Structure: [{"action": {...}, "result": "success|failed", "error": "..."}]

    # Error information
    error: str | None = Field(default=None, sa_column=Column(Text))

    # Relationships
    workflow: Workflow = Relationship(back_populates="executions")
    message: "Message" = Relationship(back_populates="workflow_executions")


class WorkflowCreate(WorkflowBase):
    """Schema for creating a workflow."""

    trigger: dict
    actions: list[dict]


class WorkflowRead(WorkflowBase):
    """Schema for reading a workflow."""

    id: UUID
    tenant_id: UUID
    trigger: dict
    actions: list[dict]


class WorkflowUpdate(SQLModel):
    """Schema for updating a workflow."""

    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    priority: int | None = None
    trigger: dict | None = None
    actions: list[dict] | None = None


class WorkflowExecutionRead(SQLModel):
    """Schema for reading workflow execution."""

    id: UUID
    workflow_id: UUID
    message_id: UUID
    triggered_at: datetime
    completed_at: datetime | None
    status: ExecutionStatus
    actions_executed: list[dict]
    error: str | None
