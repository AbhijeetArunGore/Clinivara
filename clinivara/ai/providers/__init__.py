"""
LLM Provider module and factory.
"""

from clinivara.ai.providers.base import LLMProvider
from clinivara.ai.providers.mock_provider import MockLLMProvider
from clinivara.ai.providers.openai_provider import OpenAICompatibleProvider
from clinivara.core.config import get_settings


def get_llm_provider() -> LLMProvider:
    """Return configured LLM provider according to deployment settings."""
    settings = get_settings()
    if settings.llm_provider == "openai" or settings.enable_external_llm:
        return OpenAICompatibleProvider()
    return MockLLMProvider()


__all__ = ["LLMProvider", "MockLLMProvider", "OpenAICompatibleProvider", "get_llm_provider"]
