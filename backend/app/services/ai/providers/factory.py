"""Factory for creating AI providers based on tenant configuration."""

from typing import TYPE_CHECKING

from app.core.encryption import decrypt_value
from app.services.ai.providers.base import AIProvider, AIProviderError
from app.services.ai.providers.claude import ClaudeProvider
from app.services.ai.providers.openai import OpenAIProvider
from app.services.ai.providers.azure_openai import AzureOpenAIProvider
from app.services.ai.providers.ollama import OllamaProvider

if TYPE_CHECKING:
    from app.models.tenant import Tenant


def get_provider(tenant: "Tenant") -> AIProvider:
    """
    Get an AI provider configured for a specific tenant.

    Tenants must configure their own API keys.

    Args:
        tenant: The tenant to get provider for.

    Returns:
        Configured AIProvider instance.

    Raises:
        AIProviderError: If provider is not configured.
    """
    provider_name = tenant.ai_provider
    config = tenant.ai_provider_config.get(provider_name, {})

    match provider_name:
        case "claude":
            api_key = _decrypt_api_key(config.get("api_key_encrypted"))
            if not api_key:
                raise AIProviderError(
                    "Claude API key not configured. Add your Anthropic API key in Settings > AI Providers."
                )
            return ClaudeProvider(
                api_key=api_key,
                model=config.get("model"),
            )

        case "openai":
            api_key = _decrypt_api_key(config.get("api_key_encrypted"))
            if not api_key:
                raise AIProviderError(
                    "OpenAI API key not configured. Add your OpenAI API key in Settings > AI Providers."
                )
            return OpenAIProvider(
                api_key=api_key,
                model=config.get("model"),
            )

        case "azure_openai":
            api_key = _decrypt_api_key(config.get("api_key_encrypted"))
            endpoint = config.get("endpoint")
            deployment = config.get("deployment")
            if not api_key or not endpoint or not deployment:
                raise AIProviderError(
                    "Azure OpenAI not fully configured. Add your API key, endpoint, and deployment name in Settings > AI Providers."
                )
            return AzureOpenAIProvider(
                api_key=api_key,
                endpoint=endpoint,
                deployment_name=deployment,
                api_version=config.get("api_version", "2024-02-15-preview"),
            )

        case "ollama":
            base_url = config.get("base_url", "http://localhost:11434")
            return OllamaProvider(
                base_url=base_url,
                model=config.get("model"),
            )

        case _:
            raise AIProviderError(f"Unknown provider: {provider_name}")


def _decrypt_api_key(encrypted_key: str | None) -> str | None:
    """Decrypt an API key stored in tenant config."""
    if not encrypted_key:
        return None
    try:
        return decrypt_value(encrypted_key)
    except Exception:
        return None
