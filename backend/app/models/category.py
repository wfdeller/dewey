"""Category model for issue classification."""

from typing import TYPE_CHECKING, Literal
from uuid import UUID

from sqlalchemy import Column, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Field, Relationship, SQLModel, String

from app.models.base import TenantBaseModel

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.message import Message


# Stance labels for category assignments (5-point scale)
StanceLabel = Literal[
    "strongly_supports", "supports", "neutral", "opposes", "strongly_opposes"
]

STANCE_LABELS = [
    "strongly_supports", "supports", "neutral", "opposes", "strongly_opposes"
]


class CategoryBase(SQLModel):
    """Category base schema."""

    name: str = Field(index=True)
    description: str | None = None
    color: str = Field(default="#1890ff", max_length=7)  # Hex color
    is_active: bool = Field(default=True)
    sort_order: int = Field(default=0)


class Category(CategoryBase, TenantBaseModel, table=True):
    """Category database model with hierarchical support."""

    __tablename__ = "category"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_category_tenant_name"),)

    # Parent category for hierarchy
    parent_id: UUID | None = Field(default=None, foreign_key="category.id", index=True)

    # Keywords for rule-based matching
    keywords: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String)))

    # Relationships
    tenant: "Tenant" = Relationship(back_populates="categories")
    parent: "Category" = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "Category.id"},
    )
    children: list["Category"] = Relationship(back_populates="parent")
    message_categories: list["MessageCategory"] = Relationship(back_populates="category")


class MessageCategory(SQLModel, table=True):
    """Many-to-many relationship between messages and categories."""

    __tablename__ = "message_category"

    message_id: UUID = Field(foreign_key="message.id", primary_key=True)
    category_id: UUID = Field(foreign_key="category.id", primary_key=True)
    confidence: float | None = Field(default=None)  # AI confidence score
    is_ai_suggested: bool = Field(default=False)  # True if AI suggested, False if human assigned
    assigned_by: UUID | None = Field(default=None, foreign_key="user.id")

    # Stance: the message's position on this category/issue
    # e.g., "strongly_supports", "supports", "neutral", "opposes", "strongly_opposes"
    stance: str | None = Field(default=None)
    stance_confidence: float | None = Field(default=None, ge=0, le=1)

    # Relationships
    message: "Message" = Relationship(back_populates="message_categories")
    category: Category = Relationship(back_populates="message_categories")


class CategoryCreate(CategoryBase):
    """Schema for creating a category."""

    parent_id: UUID | None = None
    keywords: list[str] = []


class CategoryRead(CategoryBase):
    """Schema for reading a category."""

    id: UUID
    tenant_id: UUID
    parent_id: UUID | None
    keywords: list[str]


class CategoryUpdate(SQLModel):
    """Schema for updating a category."""

    name: str | None = None
    description: str | None = None
    parent_id: UUID | None = None
    color: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None
    keywords: list[str] | None = None
