"""Factory for creating AI providers based on tenant configuration."""

from typing import TYPE_CHECKING

from app.core.config import get_settings
from app.services.ai.providers.base import AIProvider, AIProviderError
from app.services.ai.providers.claude import ClaudeProvider
from app.services.ai.providers.openai import OpenAIProvider
from app.services.ai.providers.azure_openai import AzureOpenAIProvider
from app.services.ai.providers.ollama import OllamaProvider

if TYPE_CHECKING:
    from app.models.tenant import Tenant


def get_platform_provider(provider_name: str | None = None) -> AIProvider:
    """
    Get an AI provider using platform (Dewey's) API keys.

    This is used when:
    - Tenant uses platform key (ai_key_source="platform")
    - Background tasks that don't have tenant context

    Args:
        provider_name: Optional provider override. If not specified,
                      uses the platform default.

    Returns:
        Configured AIProvider instance.

    Raises:
        AIProviderError: If provider is not configured.
    """
    settings = get_settings()
    provider = provider_name or settings.default_ai_provider

    match provider:
        case "claude":
            if not settings.anthropic_api_key:
                raise AIProviderError("Anthropic API key not configured")
            return ClaudeProvider(api_key=settings.anthropic_api_key)

        case "openai":
            if not settings.openai_api_key:
                raise AIProviderError("OpenAI API key not configured")
            return OpenAIProvider(api_key=settings.openai_api_key)

        case "azure_openai":
            if not settings.azure_openai_api_key or not settings.azure_openai_endpoint:
                raise AIProviderError("Azure OpenAI not fully configured")
            # For platform key, we need a default deployment
            # This should be configured in settings
            return AzureOpenAIProvider(
                api_key=settings.azure_openai_api_key,
                endpoint=settings.azure_openai_endpoint,
                deployment_name="gpt-4o-mini",  # Default deployment
            )

        case "ollama":
            return OllamaProvider(base_url=settings.ollama_base_url)

        case _:
            raise AIProviderError(f"Unknown provider: {provider}")


def get_provider(tenant: "Tenant") -> AIProvider:
    """
    Get an AI provider configured for a specific tenant.

    Uses tenant's own API key if configured, otherwise falls back
    to platform key.

    Args:
        tenant: The tenant to get provider for.

    Returns:
        Configured AIProvider instance.

    Raises:
        AIProviderError: If provider is not configured.
    """
    provider_name = tenant.ai_provider

    # If tenant uses platform key, delegate to platform provider
    if tenant.ai_key_source == "platform":
        return get_platform_provider(provider_name)

    # Tenant has their own API key
    config = tenant.ai_provider_config.get(provider_name, {})

    match provider_name:
        case "claude":
            api_key = _decrypt_api_key(config.get("api_key_encrypted"))
            if not api_key:
                raise AIProviderError(
                    f"Tenant {tenant.id} has no Claude API key configured"
                )
            return ClaudeProvider(
                api_key=api_key,
                model=config.get("model"),
            )

        case "openai":
            api_key = _decrypt_api_key(config.get("api_key_encrypted"))
            if not api_key:
                raise AIProviderError(
                    f"Tenant {tenant.id} has no OpenAI API key configured"
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
                    f"Tenant {tenant.id} has incomplete Azure OpenAI configuration"
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
    """
    Decrypt an API key stored in tenant config.

    TODO: Implement proper encryption using Fernet or similar.
    For now, we store keys in plain text (should be encrypted in production).
    """
    if not encrypted_key:
        return None
    # TODO: Decrypt with Fernet using settings.secret_key
    # For now, assume plain text (NOT PRODUCTION READY)
    return encrypted_key


def encrypt_api_key(api_key: str) -> str:
    """
    Encrypt an API key for storage in tenant config.

    TODO: Implement proper encryption using Fernet or similar.
    """
    # TODO: Encrypt with Fernet using settings.secret_key
    # For now, store plain text (NOT PRODUCTION READY)
    return api_key
