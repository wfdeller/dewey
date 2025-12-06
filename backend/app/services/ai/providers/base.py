"""Abstract base class for AI providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AIResponse:
    """Response from an AI provider."""

    content: str
    input_tokens: int
    output_tokens: int
    model: str
    raw_response: dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.input_tokens + self.output_tokens


class AIProviderError(Exception):
    """Base exception for AI provider errors."""

    pass


class AIRateLimitError(AIProviderError):
    """Rate limit exceeded."""

    pass


class AIAuthenticationError(AIProviderError):
    """Authentication failed."""

    pass


class AIBudgetExceededError(AIProviderError):
    """Token budget exceeded."""

    pass


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'claude', 'openai')."""
        pass

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Return the default model for this provider."""
        pass

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> AIResponse:
        """
        Send a prompt and get a completion.

        Args:
            prompt: The user prompt to send.
            system_prompt: Optional system prompt for context.
            max_tokens: Maximum tokens in the response.
            temperature: Sampling temperature (0.0 to 1.0).
            model: Optional model override.

        Returns:
            AIResponse with the completion and token usage.

        Raises:
            AIProviderError: If the API call fails.
            AIRateLimitError: If rate limited.
            AIAuthenticationError: If authentication fails.
        """
        pass

    def count_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        This is a rough estimate. Providers may override with
        more accurate counting using their tokenizers.

        Args:
            text: The text to count tokens for.

        Returns:
            Estimated token count.
        """
        # Rough estimate: ~4 characters per token for English
        return len(text) // 4
