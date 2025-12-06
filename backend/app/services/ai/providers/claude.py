"""Claude (Anthropic) AI provider implementation."""

import anthropic
from anthropic import APIError, AuthenticationError, RateLimitError

from app.services.ai.providers.base import (
    AIProvider,
    AIResponse,
    AIProviderError,
    AIRateLimitError,
    AIAuthenticationError,
)


class ClaudeProvider(AIProvider):
    """Anthropic Claude provider."""

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
    ):
        """
        Initialize Claude provider.

        Args:
            api_key: Anthropic API key.
            model: Optional default model override.
        """
        self._api_key = api_key
        self._model = model or self.default_model
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "claude"

    @property
    def default_model(self) -> str:
        return "claude-3-haiku-20240307"

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> AIResponse:
        """Send prompt to Claude and get completion."""
        try:
            message = await self._client.messages.create(
                model=model or self._model,
                max_tokens=max_tokens,
                system=system_prompt or "",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )

            # Extract content
            content = ""
            if message.content:
                content = message.content[0].text

            return AIResponse(
                content=content,
                input_tokens=message.usage.input_tokens,
                output_tokens=message.usage.output_tokens,
                model=message.model,
                raw_response={
                    "id": message.id,
                    "type": message.type,
                    "role": message.role,
                    "stop_reason": message.stop_reason,
                },
            )

        except AuthenticationError as e:
            raise AIAuthenticationError(f"Claude authentication failed: {e}") from e
        except RateLimitError as e:
            raise AIRateLimitError(f"Claude rate limit exceeded: {e}") from e
        except APIError as e:
            raise AIProviderError(f"Claude API error: {e}") from e

    def count_tokens(self, text: str) -> int:
        """
        Estimate token count for Claude.

        Claude uses a similar tokenizer to GPT models.
        This is a rough estimate.
        """
        # Claude averages ~4 characters per token for English
        return len(text) // 4
