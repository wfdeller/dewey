"""Azure OpenAI AI provider implementation."""

from openai import AsyncAzureOpenAI, APIError, AuthenticationError, RateLimitError

from app.services.ai.providers.base import (
    AIProvider,
    AIResponse,
    AIProviderError,
    AIRateLimitError,
    AIAuthenticationError,
)


class AzureOpenAIProvider(AIProvider):
    """Azure OpenAI provider."""

    def __init__(
        self,
        api_key: str,
        endpoint: str,
        deployment_name: str,
        api_version: str = "2024-02-15-preview",
    ):
        """
        Initialize Azure OpenAI provider.

        Args:
            api_key: Azure OpenAI API key.
            endpoint: Azure OpenAI endpoint URL.
            deployment_name: The deployment name (model deployment).
            api_version: API version to use.
        """
        self._api_key = api_key
        self._endpoint = endpoint
        self._deployment_name = deployment_name
        self._api_version = api_version
        self._client = AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
        )

    @property
    def provider_name(self) -> str:
        return "azure_openai"

    @property
    def default_model(self) -> str:
        # Azure uses deployment names, not model names
        return self._deployment_name

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> AIResponse:
        """Send prompt to Azure OpenAI and get completion."""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # Azure OpenAI uses deployment name instead of model
            deployment = model or self._deployment_name

            response = await self._client.chat.completions.create(
                model=deployment,
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
                    "deployment": deployment,
                },
            )

        except AuthenticationError as e:
            raise AIAuthenticationError(
                f"Azure OpenAI authentication failed: {e}"
            ) from e
        except RateLimitError as e:
            raise AIRateLimitError(f"Azure OpenAI rate limit exceeded: {e}") from e
        except APIError as e:
            raise AIProviderError(f"Azure OpenAI API error: {e}") from e

    def count_tokens(self, text: str) -> int:
        """
        Estimate token count for Azure OpenAI.

        Uses same tokenization as OpenAI.
        """
        return len(text) // 4
