"""
OpenAI-compatible LLM Provider implementation for external inference (OpenAI, vLLM, Ollama, LiteLLM).
Enforces security boundaries: rejects external transmission unless explicitly authorized by deployment configuration.
"""

import json
from typing import Any, Dict, Optional, Type
import httpx
from pydantic import BaseModel, ValidationError

from clinivara.ai.providers.base import LLMProvider
from clinivara.core.config import get_settings


class OpenAICompatibleProvider(LLMProvider):
    """Provider adapter for OpenAI-compatible APIs with strict privacy gates."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.openai_api_key
        self.base_url = (base_url or settings.openai_base_url).rstrip("/")
        self.model = model or settings.llm_model_name
        self.timeout = timeout or settings.llm_request_timeout_seconds
        self.enable_external = settings.enable_external_llm

    def _check_policy(self) -> None:
        """Enforce Non-Negotiable Rule #8: Prohibit unauthorized external transmission."""
        if not self.enable_external:
            raise PermissionError(
                "External LLM calls are prohibited by current security deployment policy. "
                "Set ENABLE_EXTERNAL_LLM=true in verified environment to permit external transmission."
            )
        if not self.api_key and "localhost" not in self.base_url and "127.0.0.1" not in self.base_url:
            raise ValueError("OPENAI_API_KEY is required for external LLM endpoint.")

    def health_check(self) -> Dict[str, Any]:
        if not self.enable_external:
            return {
                "status": "disabled_by_policy",
                "provider": "openai_compatible",
                "enable_external_llm": False,
            }
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            with httpx.Client(timeout=5.0) as client:
                res = client.get(f"{self.base_url}/models", headers=headers)
                if res.status_code == 200:
                    return {"status": "healthy", "provider": "openai_compatible", "base_url": self.base_url}
                return {"status": "degraded", "code": res.status_code}
        except Exception as err:
            return {"status": "unreachable", "error": type(err).__name__}

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ) -> str:
        self._check_policy()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[BaseModel],
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
    ) -> BaseModel:
        self._check_policy()

        schema_json = json.dumps(response_model.model_json_schema())
        augmented_system = (
            f"{system_prompt or ''}\n\n"
            f"You MUST reply strictly with a JSON object conforming exactly to this JSON schema:\n"
            f"{schema_json}\nDo not include code markdown fences or explanations outside the JSON."
        )

        raw_output = self.generate(
            prompt=prompt,
            system_prompt=augmented_system,
            temperature=temperature,
            max_tokens=2500,
        )

        cleaned = raw_output.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return response_model.model_validate_json(cleaned)
        except ValidationError as err:
            # Bounded one-shot repair
            repair_prompt = f"The previous output failed validation: {err}.\nPlease fix and return strictly valid JSON for the schema:\n{cleaned}"
            repaired = self.generate(prompt=repair_prompt, system_prompt=augmented_system, temperature=0.0)
            clean_rep = repaired.strip()
            if clean_rep.startswith("```json"):
                clean_rep = clean_rep[7:]
            if clean_rep.startswith("```"):
                clean_rep = clean_rep[3:]
            if clean_rep.endswith("```"):
                clean_rep = clean_rep[:-3]
            return response_model.model_validate_json(clean_rep.strip())
