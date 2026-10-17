"""
Application Configuration with secure defaults and typed validation.
"""

import json
import os
from pathlib import Path
from typing import List, Literal, Optional, Set

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_api_keys() -> dict[str, str]:
    """Load API key mapping from CLINIVARA_API_KEYS or return a demo-safe fallback."""
    raw = os.getenv("CLINIVARA_API_KEYS")
    if raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "CLINIVARA_API_KEYS must be a JSON object mapping API keys to tenant IDs."
            ) from exc

        if not isinstance(parsed, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in parsed.items()
        ):
            raise ValueError(
                "CLINIVARA_API_KEYS must be a JSON object mapping API keys to tenant IDs."
            )
        return parsed

    # Demo-safe defaults only; override in local .env or a secrets manager.
    return {
        "sample-dev-api-key": "clinic_default_tenant",
        "sample-test-api-key": "clinic_tenant_two",
    }


class Settings(BaseSettings):
    """
    Clinivara system settings loaded from environment variables with secure defaults.
    """
    model_config = SettingsConfigDict(
        env_prefix="CLINIVARA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Runtime Environment
    app_name: str = "Clinivara Clinical Processing Backend"
    app_version: str = "1.0.0"
    app_env: Literal["development", "testing", "staging", "production"] = "development"
    debug: bool = False

    # Security & API Authentication
    # Real production values must come from local environment or a managed secret store.
    auth_secret_key: str = Field(default="REPLACE_WITH_32_BYTE_SECRET", min_length=16)
    api_key_header_name: str = "X-API-Key"
    api_keys: dict[str, str] = Field(default_factory=_load_api_keys)

    # Trust Boundaries & Storage Paths
    storage_root: Path = Path("data/storage")
    max_upload_size_bytes: int = 25 * 1024 * 1024  # 25 MB max document upload
    max_pdf_pages: int = 50                        # Max pages per document
    max_image_dimension_pixels: int = 8000         # Max dimension to prevent decompression bombs
    max_image_pixels: int = 50_000_000             # 50 MP threshold

    # Ingestion constraints
    allowed_extensions: Set[str] = {".pdf", ".png", ".jpg", ".jpeg"}
    allowed_mime_types: Set[str] = {
        "application/pdf",
        "image/png",
        "image/jpeg",
    }

    # OCR Pipeline Configuration
    ocr_enabled: bool = True
    ocr_default_language: str = "eng"
    ocr_fallback_char_threshold: int = 50          # Trigger OCR if digital text < 50 chars/page
    ocr_dpi: int = 300                             # Optimal rendering resolution for Tesseract
    ocr_timeout_seconds: int = 30                  # Max OCR processing time per page

    # De-identification & Privacy Policy
    deid_policy_version: str = "1.0"
    deid_confidence_threshold: float = 0.60
    # Redaction style: [NAME], [PATIENT_ID], [DATE], etc.
    mask_format: str = "[{entity_type}]"
    date_policy: Literal["redact", "generalize_year", "shift"] = "redact"
    enable_longitudinal_tokens: bool = False
    tokenization_salt: str = "REPLACE_WITH_HIGH_ENTROPY_SALT"

    # Audit & Observability
    audit_log_path: Path = Path("data/audit/audit_events.jsonl")
    log_level: str = "INFO"

    # AI Subsystem & LLM Orchestration
    # Safe default: mock provider for deterministic, zero-cost, offline operation
    llm_provider: Literal["mock", "openai", "local"] = "mock"
    llm_model: str = "gpt-4o-mini"
    llm_model_name: str = "gpt-4o-mini"
    llm_base_url: Optional[str] = None
    openai_base_url: str = "https://api.openai.com/v1"
    llm_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    llm_timeout_seconds: int = 30
    llm_request_timeout_seconds: int = 30
    llm_max_retries: int = 3
    llm_temperature: float = 0.0
    enable_external_llm: bool = False  # Privacy safeguard: external transmission disabled unless explicitly enabled

    # Multilingual Configuration
    supported_languages: List[str] = Field(default_factory=lambda: ["en", "hi", "mr"])
    default_language: str = "en"
    ocr_language_packs: List[str] = Field(default_factory=lambda: ["eng", "hin", "mar"])

    # Clinical RAG Configuration
    embedding_provider: Literal["local_tfidf", "dense", "mock"] = "local_tfidf"
    embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    rag_top_k: int = 4
    rag_relevance_threshold: float = 0.10
    rag_max_chunk_tokens: int = 300
    vector_store_root: Path = Path("data/storage/vector_store")

    @field_validator("deid_confidence_threshold")
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("deid_confidence_threshold must be between 0.0 and 1.0")
        return v

    @model_validator(mode="after")
    def validate_runtime_secret_configuration(self):
        placeholder_values = {
            "REPLACE_WITH_32_BYTE_SECRET",
            "REPLACE_WITH_HIGH_ENTROPY_SALT",
            "sample-dev-api-key",
            "sample-test-api-key",
        }

        if self.app_env == "production":
            if not self.api_keys:
                raise ValueError(
                    "Production API keys must be configured via the CLINIVARA_API_KEYS environment variable."
                )
            if any(k in placeholder_values for k in self.api_keys):
                raise ValueError(
                    "Production API keys must not use placeholder values; set CLINIVARA_API_KEYS to real values."
                )
            if self.auth_secret_key in {"REPLACE_WITH_32_BYTE_SECRET", ""}:
                raise ValueError(
                    "Production authentication secret is missing; set CLINIVARA_AUTH_SECRET_KEY in the environment."
                )
            if self.tokenization_salt in {"REPLACE_WITH_HIGH_ENTROPY_SALT", ""}:
                raise ValueError(
                    "Production tokenization salt is missing; set CLINIVARA_TOKENIZATION_SALT in the environment."
                )
        return self

    @property
    def boundary_a_raw_dir(self) -> Path:
        """Boundary A: Restricted original uploaded documents."""
        return self.storage_root / "boundary_a_raw"

    @property
    def boundary_b_scratch_dir(self) -> Path:
        """Boundary B: Intermediate processing artifacts and temporary OCR renders."""
        return self.storage_root / "boundary_b_scratch"

    @property
    def boundary_c_approved_dir(self) -> Path:
        """Boundary C: Independent-verified and policy-approved de-identified outputs."""
        return self.storage_root / "boundary_c_approved"

    @property
    def token_vault_dir(self) -> Path:
        """Isolated token vault for pseudonymization linkage (never exposed)."""
        return self.storage_root / "token_vault"


# Global singleton instance
settings = Settings()


def get_settings() -> Settings:
    """Return the global settings instance."""
    return settings
