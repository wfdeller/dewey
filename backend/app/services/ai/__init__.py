"""AI provider services package."""

from app.services.ai.providers import (
    AIProvider,
    AIResponse,
    ClaudeProvider,
    OpenAIProvider,
    AzureOpenAIProvider,
    OllamaProvider,
    get_provider,
)
from app.services.ai.providers.base import (
    AIProviderError,
    AIRateLimitError,
    AIAuthenticationError,
    AIBudgetExceededError,
)
from app.services.ai.message_analyzer import MessageAnalyzer

__all__ = [
    # Base classes
    "AIProvider",
    "AIResponse",
    # Providers
    "ClaudeProvider",
    "OpenAIProvider",
    "AzureOpenAIProvider",
    "OllamaProvider",
    # Factory
    "get_provider",
    # Exceptions
    "AIProviderError",
    "AIRateLimitError",
    "AIAuthenticationError",
    "AIBudgetExceededError",
    # Services
    "MessageAnalyzer",
]
