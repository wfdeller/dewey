"""Message analysis service using AI providers."""

import json
import re
import time
from typing import Any
from uuid import UUID

from jinja2 import Template
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.analysis import Analysis
from app.models.category import Category
from app.models.message import Message
from app.models.tenant import Tenant
from app.models.ai_usage_log import AIUsageLog
from app.models.prompt_template import PromptTemplate as PromptTemplateModel
from app.services.ai.providers import get_provider, AIResponse
from app.services.ai.providers.base import AIProviderError
from app.services.ai.prompts.defaults import get_default_prompt, PromptTemplate


class MessageAnalyzer:
    """Core service for analyzing messages with AI."""

    def __init__(
        self,
        session: AsyncSession,
        tenant: Tenant,
        user_id: UUID | None = None,
    ):
        """
        Initialize the message analyzer.

        Args:
            session: Database session.
            tenant: The tenant to analyze messages for.
            user_id: Optional user ID for logging.
        """
        self.session = session
        self.tenant = tenant
        self.user_id = user_id
        self.provider = get_provider(tenant)

    async def analyze(
        self,
        message: Message,
        include_response_suggestion: bool = False,
    ) -> Analysis:
        """
        Run full analysis on a message.

        Args:
            message: The message to analyze.
            include_response_suggestion: Whether to include a suggested response.

        Returns:
            Analysis record with results.

        Raises:
            AIProviderError: If AI provider fails or is not configured.
        """
        # Get prompt template (custom or default)
        template = await self._get_template("message_analysis")

        # Get categories for classification
        categories = await self._get_categories()

        # Render prompt using Jinja2
        prompt = self._render_prompt(
            template.user_prompt_template,
            message=message,
            categories=categories,
            include_response_suggestion=include_response_suggestion,
        )

        # Call AI provider
        start_time = time.time()
        response = await self.provider.complete(
            prompt=prompt,
            system_prompt=template.system_prompt,
            temperature=template.temperature,
            max_tokens=template.max_tokens,
        )
        processing_time = int((time.time() - start_time) * 1000)

        # Parse response
        analysis_data = self._parse_response(response.content)

        # Convert tones to expected format if needed
        tones = analysis_data.get("tones", [])
        if tones and isinstance(tones[0], str):
            # Convert simple string list to dict format with default confidence
            tones = [{"label": t, "confidence": 0.8} for t in tones]

        # Create Analysis record
        analysis = Analysis(
            message_id=message.id,
            tones=tones,
            summary=analysis_data.get("summary", ""),
            urgency_score=analysis_data.get("urgency_score", 0.5),
            entities=self._normalize_entities(analysis_data.get("entities", {})),
            suggested_categories=self._normalize_categories(
                analysis_data.get("suggested_categories", [])
            ),
            suggested_response=analysis_data.get("suggested_response"),
            ai_provider=self.provider.provider_name,
            ai_model=response.model,
            tokens_used=response.total_tokens,
            processing_time_ms=processing_time,
            raw_response={"content": response.content, **response.raw_response},
        )

        # Log AI usage
        await self._log_usage(
            operation_type="message_analysis",
            operation_id=str(message.id),
            response=response,
            processing_time_ms=processing_time,
            status="success",
        )

        # Add analysis to session
        self.session.add(analysis)
        await self.session.commit()
        await self.session.refresh(analysis)

        return analysis

    async def _get_template(self, name: str) -> PromptTemplate:
        """
        Get prompt template for tenant (custom or default).

        Args:
            name: Template name.

        Returns:
            PromptTemplate (either from DB or default).
        """
        # Try to get custom template from database
        result = await self.session.execute(
            select(PromptTemplateModel).where(
                PromptTemplateModel.tenant_id == self.tenant.id,
                PromptTemplateModel.name == name,
                PromptTemplateModel.is_active == True,  # noqa: E712
            )
        )
        db_template = result.scalar_one_or_none()

        if db_template:
            # Convert DB model to PromptTemplate dataclass
            return PromptTemplate(
                name=db_template.name,
                description=db_template.description or "",
                system_prompt=db_template.system_prompt,
                user_prompt_template=db_template.user_prompt_template,
                temperature=db_template.temperature,
                max_tokens=db_template.max_tokens,
            )

        # Fall back to default
        default = get_default_prompt(name)
        if not default:
            raise ValueError(f"No prompt template found for: {name}")
        return default

    async def _get_categories(self) -> list[Category]:
        """Get active categories for the tenant."""
        result = await self.session.execute(
            select(Category).where(
                Category.tenant_id == self.tenant.id,
                Category.is_active == True,  # noqa: E712
            )
        )
        return list(result.scalars().all())

    def _render_prompt(
        self,
        template_str: str,
        **context: Any,
    ) -> str:
        """
        Render a Jinja2 prompt template.

        Args:
            template_str: The Jinja2 template string.
            **context: Variables to pass to the template.

        Returns:
            Rendered prompt string.
        """
        template = Template(template_str)
        return template.render(**context)

    def _parse_response(self, content: str) -> dict[str, Any]:
        """
        Parse AI response content as JSON.

        Handles markdown code blocks and partial responses.

        Args:
            content: Raw response content from AI.

        Returns:
            Parsed dictionary with analysis results.
        """
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if json_match:
            content = json_match.group(1)

        # Try to find JSON object in the content
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # If we can't parse JSON, return a minimal result
        return {
            "tones": ["neutral"],
            "summary": "Unable to analyze message",
            "urgency_score": 0.5,
            "entities": {},
            "suggested_categories": [],
            "parse_error": True,
            "raw_content": content[:500],
        }

    async def _log_usage(
        self,
        operation_type: str,
        operation_id: str,
        response: AIResponse,
        processing_time_ms: int,
        status: str = "success",
        error_message: str | None = None,
    ) -> None:
        """Log AI API usage for analytics."""
        log = AIUsageLog(
            tenant_id=self.tenant.id,
            operation_type=operation_type,
            operation_id=operation_id,
            ai_provider=self.provider.provider_name,
            ai_model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            total_tokens=response.total_tokens,
            processing_time_ms=processing_time_ms,
            status=status,
            error_message=error_message,
            user_id=self.user_id,
        )
        self.session.add(log)

    def _normalize_entities(self, entities: dict[str, Any] | list) -> list[dict]:
        """
        Normalize entities to expected format.

        Input format from AI:
        {"people": ["John"], "organizations": ["EPA"], "locations": ["DC"]}

        Output format for DB:
        [{"type": "person", "value": "John"}, {"type": "organization", "value": "EPA"}]
        """
        if isinstance(entities, list):
            return entities

        result = []
        type_mapping = {
            "people": "person",
            "organizations": "organization",
            "locations": "location",
            "topics": "topic",
        }

        for key, values in entities.items():
            entity_type = type_mapping.get(key, key)
            if isinstance(values, list):
                for value in values:
                    result.append({"type": entity_type, "value": value})

        return result

    def _normalize_categories(
        self, categories: list[str] | list[dict]
    ) -> list[dict]:
        """
        Normalize category suggestions to expected format.

        Input format from AI:
        ["Healthcare", "Environment"]

        Output format for DB:
        [{"category_name": "Healthcare", "confidence": 0.8}]
        """
        if not categories:
            return []

        if isinstance(categories[0], dict):
            return categories

        return [{"category_name": cat, "confidence": 0.8} for cat in categories]
