"""Ollama AI provider implementation."""

import httpx

from app.services.ai.providers.base import (
    AIProvider,
    AIResponse,
    AIProviderError,
)


class OllamaProvider(AIProvider):
    """Ollama local LLM provider."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str | None = None,
    ):
        """
        Initialize Ollama provider.

        Args:
            base_url: Ollama server URL.
            model: Optional default model override.
        """
        self._base_url = base_url.rstrip("/")
        self._model = model or self.default_model

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def default_model(self) -> str:
        return "llama3.2"

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> AIResponse:
        """Send prompt to Ollama and get completion."""
        try:
            # Build messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self._base_url}/api/chat",
                    json={
                        "model": model or self._model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens,
                        },
                    },
                )

                if response.status_code != 200:
                    raise AIProviderError(
                        f"Ollama API error: {response.status_code} - {response.text}"
                    )

                data = response.json()

                # Extract content
                content = data.get("message", {}).get("content", "")

                # Get token usage (Ollama provides these in some versions)
                input_tokens = data.get("prompt_eval_count", 0)
                output_tokens = data.get("eval_count", 0)

                # Estimate tokens if not provided
                if input_tokens == 0:
                    input_tokens = self.count_tokens(
                        (system_prompt or "") + prompt
                    )
                if output_tokens == 0:
                    output_tokens = self.count_tokens(content)

                return AIResponse(
                    content=content,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    model=data.get("model", model or self._model),
                    raw_response={
                        "done": data.get("done"),
                        "done_reason": data.get("done_reason"),
                        "total_duration": data.get("total_duration"),
                        "load_duration": data.get("load_duration"),
                        "eval_duration": data.get("eval_duration"),
                    },
                )

        except httpx.ConnectError as e:
            raise AIProviderError(
                f"Cannot connect to Ollama at {self._base_url}: {e}"
            ) from e
        except httpx.TimeoutException as e:
            raise AIProviderError(f"Ollama request timed out: {e}") from e
        except Exception as e:
            if isinstance(e, AIProviderError):
                raise
            raise AIProviderError(f"Ollama error: {e}") from e

    def count_tokens(self, text: str) -> int:
        """
        Estimate token count for Ollama.

        Different models have different tokenizers, so this is a rough estimate.
        """
        # Rough estimate: ~4 characters per token
        return len(text) // 4
