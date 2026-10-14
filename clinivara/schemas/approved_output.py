"""
Strict Pydantic models for approved clinical document outputs.
Enforces the invariant that unapproved or unvalidated documents cannot be serialized.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ClinicalSection(BaseModel):
    """Normalized clinical section preserving clinical context."""
    model_config = ConfigDict(frozen=True)

    title: str = Field(description="Normalized section heading (e.g. DIAGNOSIS, MEDICATIONS)")
    content: str = Field(description="De-identified text within this clinical section")


class ExtractionMetadata(BaseModel):
    """Safe extraction summary without disclosing raw text or sensitive paths."""
    model_config = ConfigDict(frozen=True)

    status: Literal["COMPLETED", "PARTIAL", "FAILED"]
    pages_processed: int = Field(ge=1)
    methods_used: List[str] = Field(description="Extraction mechanisms used, e.g. digital_text, ocr")
    warnings: List[str] = Field(default_factory=list)


class DeidentificationMetadata(BaseModel):
    """Summary of privacy transformations applied."""
    model_config = ConfigDict(frozen=True)

    status: Literal["COMPLETED", "FAILED"]
    policy_version: str = Field(default="1.0")
    validation_status: Literal["PASSED", "FAILED", "REVIEW_REQUIRED"]
    transformed_entity_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Safe counts of masked entity types (e.g. {'NAME': 2, 'PHONE': 1}) without leaking values",
    )


class QualityMetadata(BaseModel):
    """Quality and preservation verification flags."""
    model_config = ConfigDict(frozen=True)

    schema_valid: bool = True
    clinical_content_preserved: bool = True
    residual_identifiers_detected: int = Field(default=0, ge=0)


class ClinicalContent(BaseModel):
    """De-identified clinical text and structured sections."""
    model_config = ConfigDict(frozen=True)

    text: str = Field(description="Fully sanitized, de-identified clinical text")
    sections: List[ClinicalSection] = Field(default_factory=list)


class ApprovedDocumentOutput(BaseModel):
    """
    Downstream consumption contract.
    Only policy-approved, independently verified documents may be exported.
    """
    model_config = ConfigDict(frozen=True)

    schema_version: str = Field(default="1.0")
    document_id: str = Field(description="Random server-generated document identifier")
    tenant_id: str = Field(description="Authorized tenant/organization ID")
    processing_status: Literal["APPROVED"] = Field(
        default="APPROVED",
        description="Guaranteed APPROVED release gate state",
    )
    extraction: ExtractionMetadata
    deidentification: DeidentificationMetadata
    clinical_content: ClinicalContent
    quality: QualityMetadata

    @model_validator(mode="after")
    def verify_release_invariant(self) -> "ApprovedDocumentOutput":
        """Strict validation ensuring unsafe outputs can never be instantiated."""
        if self.processing_status != "APPROVED":
            raise ValueError("Only documents with status 'APPROVED' may be serialized in ApprovedDocumentOutput.")
        if self.deidentification.validation_status != "PASSED":
            raise ValueError("Document validation_status must be 'PASSED' for approved release.")
        if self.quality.residual_identifiers_detected > 0:
            raise ValueError("Approved document cannot contain residual detected identifiers.")
        return self
