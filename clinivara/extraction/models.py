"""
Typed internal models for extraction results and page provenance.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class PageExtraction(BaseModel):
    """Extraction result for a single page with provenance and quality signals."""
    model_config = ConfigDict(frozen=True)

    page_number: int = Field(ge=1)
    method: Literal["DIGITAL_TEXT", "OCR_FALLBACK", "IMAGE_DIRECT", "FAILED"]
    text: str = Field(description="Extracted raw text for this page (restricted to Boundary B)")
    character_count: int = Field(ge=0)
    word_count: int = Field(ge=0)
    ocr_confidence: Optional[float] = Field(
        default=None,
        description="Average OCR confidence score (0-100) if derived from OCR, else None",
    )
    warnings: List[str] = Field(default_factory=list)
    quality_signals: Dict[str, Any] = Field(default_factory=dict)


class ExtractionResult(BaseModel):
    """Internal typed extraction representation across the document."""
    model_config = ConfigDict(frozen=True)

    document_id: str
    tenant_id: str
    correlation_id: str
    pages: List[PageExtraction]
    methods_used: List[str]
    total_pages: int
    warnings: List[str] = Field(default_factory=list)
    status: Literal["COMPLETED", "PARTIAL", "FAILED"]

    def aggregate_text(self) -> str:
        """Combine page texts with explicit page boundary delimiters."""
        return "\n\n--- [PAGE BREAK] ---\n\n".join(
            p.text for p in sorted(self.pages, key=lambda x: x.page_number)
        )
