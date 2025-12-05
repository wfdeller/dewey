"""Analysis model for AI-generated message analysis."""

from typing import TYPE_CHECKING, Literal
from uuid import UUID

from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.message import Message


# Deprecated - kept for backwards compatibility
SentimentLabel = Literal["positive", "neutral", "negative"]

# New tone system - emotional and communication style labels
ToneLabel = Literal[
    # Emotional tones
    "angry", "frustrated", "grateful", "hopeful", "anxious",
    "disappointed", "enthusiastic", "satisfied", "confused", "concerned",
    # Communication style tones
    "cordial", "formal", "informal", "urgent", "demanding",
    "polite", "hostile", "professional", "casual", "apologetic"
]

# All valid tone labels as a list for validation
TONE_LABELS = [
    "angry", "frustrated", "grateful", "hopeful", "anxious",
    "disappointed", "enthusiastic", "satisfied", "confused", "concerned",
    "cordial", "formal", "informal", "urgent", "demanding",
    "polite", "hostile", "professional", "casual", "apologetic"
]


class AnalysisBase(SQLModel):
    """Analysis base schema."""

    # New tone system (multiple tones per message)
    # Structure: [{"label": "grateful", "confidence": 0.85}, {"label": "formal", "confidence": 0.72}]
    tones: list[dict] = Field(default_factory=list, sa_column=Column(JSONB))

    # Deprecated sentiment fields - kept nullable for migration period
    sentiment_score: float | None = Field(default=None, ge=-1, le=1)
    sentiment_label: str | None = Field(default=None)
    sentiment_confidence: float | None = Field(default=None, ge=0, le=1)

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


class ToneScore(SQLModel):
    """Schema for a tone with confidence score."""

    label: str
    confidence: float = Field(ge=0, le=1)


class AnalysisCreate(SQLModel):
    """Schema for creating an analysis."""

    message_id: UUID

    # New tone system
    tones: list[ToneScore] = []

    # Deprecated sentiment fields (optional for backwards compatibility)
    sentiment_score: float | None = None
    sentiment_label: str | None = None
    sentiment_confidence: float | None = None

    # Other fields
    summary: str
    urgency_score: float = Field(ge=0, le=1)
    entities: list[dict] = []
    suggested_categories: list[dict] = []
    suggested_response: str | None = None
    ai_provider: str
    ai_model: str
    tokens_used: int = 0
    processing_time_ms: int = 0


class AnalysisRead(SQLModel):
    """Schema for reading an analysis."""

    id: UUID
    message_id: UUID

    # New tone system
    tones: list[ToneScore]

    # Deprecated sentiment fields
    sentiment_score: float | None
    sentiment_label: str | None
    sentiment_confidence: float | None

    # Other fields
    summary: str
    urgency_score: float
    entities: list[dict]
    suggested_categories: list[dict]
    suggested_response: str | None
    ai_provider: str
    ai_model: str
