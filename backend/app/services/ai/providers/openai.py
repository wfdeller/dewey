"""OpenAI AI provider implementation."""

from openai import AsyncOpenAI, APIError, AuthenticationError, RateLimitError

from app.services.ai.providers.base import (
    AIProvider,
    AIResponse,
    AIProviderError,
    AIRateLimitError,
    AIAuthenticationError,
)


class OpenAIProvider(AIProvider):
    """OpenAI provider."""

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
    ):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key.
            model: Optional default model override.
        """
        self._api_key = api_key
        self._model = model or self.default_model
        self._client = AsyncOpenAI(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def default_model(self) -> str:
        return "gpt-4o-mini"

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> AIResponse:
        """Send prompt to OpenAI and get completion."""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = await self._client.chat.completions.create(
                model=model or self._model,
                max_tokens=max_tokens,
                messages=messages,
                temperature=temperature,
            )

            # Extract content
            content = ""
            if response.choices:
                content = response.choices[0].message.content or ""

            # Get token usage
            input_tokens = 0
            output_tokens = 0
            if response.usage:
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens

            return AIResponse(
                content=content,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model=response.model,
                raw_response={
                    "id": response.id,
                    "object": response.object,
                    "created": response.created,
                    "finish_reason": (
                        response.choices[0].finish_reason if response.choices else None
                    ),
                },
            )

        except AuthenticationError as e:
            raise AIAuthenticationError(f"OpenAI authentication failed: {e}") from e
        except RateLimitError as e:
            raise AIRateLimitError(f"OpenAI rate limit exceeded: {e}") from e
        except APIError as e:
            raise AIProviderError(f"OpenAI API error: {e}") from e

    def count_tokens(self, text: str) -> int:
        """
        Estimate token count for OpenAI.

        For more accurate counting, use tiktoken library.
        This is a rough estimate.
        """
        # GPT models average ~4 characters per token for English
        return len(text) // 4
