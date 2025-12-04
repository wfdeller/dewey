"""Analysis model for AI-generated message analysis."""

from typing import TYPE_CHECKING, Literal
from uuid import UUID

from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.message import Message


SentimentLabel = Literal["positive", "neutral", "negative"]


class AnalysisBase(SQLModel):
    """Analysis base schema."""

    # Sentiment analysis
    sentiment_score: float = Field(ge=-1, le=1)  # -1 (negative) to 1 (positive)
    sentiment_label: str  # positive, neutral, negative
    sentiment_confidence: float = Field(ge=0, le=1)

    # AI-generated summary
    summary: str = Field(sa_column=Column(Text))

    # Urgency score
    urgency_score: float = Field(ge=0, le=1)


class Analysis(AnalysisBase, BaseModel, table=True):
    """Analysis database model."""

    __tablename__ = "analysis"

    # Foreign key to message (1:1 relationship)
    message_id: UUID = Field(foreign_key="message.id", unique=True, index=True)

    # Extracted entities
    entities: list[dict] = Field(default_factory=list, sa_column=Column(JSONB))
    # Structure: [{"type": "person|org|location|topic", "value": "...", "confidence": 0.95}]

    # AI-suggested categories
    suggested_categories: list[dict] = Field(default_factory=list, sa_column=Column(JSONB))
    # Structure: [{"category_id": "uuid", "confidence": 0.85}]

    # AI-generated response suggestion
    suggested_response: str | None = Field(default=None, sa_column=Column(Text))

    # AI provider metadata
    ai_provider: str = Field(index=True)  # claude, openai, azure_openai, ollama
    ai_model: str  # claude-3-sonnet, gpt-4-turbo, etc.
    tokens_used: int = Field(default=0)
    processing_time_ms: int = Field(default=0)

    # Raw response for debugging
    raw_response: dict = Field(default_factory=dict, sa_column=Column(JSONB))

    # Relationship
    message: "Message" = Relationship(back_populates="analysis")


class AnalysisCreate(AnalysisBase):
    """Schema for creating an analysis."""

    message_id: UUID
    entities: list[dict] = []
    suggested_categories: list[dict] = []
    suggested_response: str | None = None
    ai_provider: str
    ai_model: str
    tokens_used: int = 0
    processing_time_ms: int = 0


class AnalysisRead(AnalysisBase):
    """Schema for reading an analysis."""

    id: UUID
    message_id: UUID
    entities: list[dict]
    suggested_categories: list[dict]
    suggested_response: str | None
    ai_provider: str
    ai_model: str
