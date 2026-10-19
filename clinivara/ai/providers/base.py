"""
Abstract Base Class for LLM and AI Generation Providers.
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class LLMProvider(ABC):
    """Provider-neutral LLM generation interface."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ) -> str:
        """Generate unstructured text response."""
        pass

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        response_model: type[BaseModel],
        system_prompt: str | None = None,
        temperature: float = 0.0,
    ) -> BaseModel:
        """Generate schema-constrained Pydantic model response."""
        pass

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Check provider connectivity and model availability."""
        pass
