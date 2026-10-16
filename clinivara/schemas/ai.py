"""
Strongly-typed Pydantic v2 schemas for Clinical AI, Fact Extraction, Multilingual Understanding, and RAG.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReferenceRange(BaseModel):
    """Structured representation of a laboratory reference interval."""
    model_config = ConfigDict(frozen=True)

    raw_text: str = Field(description="Exact reference range reported in source document")
    low: Optional[float] = Field(default=None, description="Lower bound numeric value")
    high: Optional[float] = Field(default=None, description="Upper bound numeric value")
    unit: Optional[str] = Field(default=None, description="Reported unit for reference range")


class ClinicalObservation(BaseModel):
    """Individual clinical/laboratory observation with strict evidence provenance."""
    model_config = ConfigDict(frozen=True)

    observation_id: str = Field(description="Unique observation identifier")
    test_name: str = Field(description="Cleaned test or parameter name")
    original_test_name: str = Field(description="Exact verbatim test name from source report")
    normalized_test_name: Optional[str] = Field(default=None, description="Canonical terminology name (e.g. LOINC display)")
    loinc_code: Optional[str] = Field(default=None, description="Standard LOINC code if mapped")
    original_value: str = Field(description="Verbatim reported measurement value")
    numeric_value: Optional[float] = Field(default=None, description="Parsed floating-point value if numeric")
    comparator: Optional[Literal["<", ">", "<=", ">=", "="]] = Field(default=None, description="Inequality comparator")
    original_unit: Optional[str] = Field(default=None, description="Verbatim unit from document")
    normalized_unit: Optional[str] = Field(default=None, description="Canonical unit (e.g. UCUM standard)")
    reference_range: Optional[ReferenceRange] = Field(default=None, description="Reported reference interval")
    source_reported_status: Optional[str] = Field(default=None, description="Flag explicitly printed in report (e.g. 'H', 'L')")
    derived_status: Literal["NORMAL", "HIGH", "LOW", "BORDERLINE", "CRITICAL", "UNKNOWN"] = Field(
        default="UNKNOWN",
        description="Software-derived evaluation against reference interval without overriding source",
    )
    is_abnormal: bool = Field(default=False, description="Flag indicating out-of-range observation")
    specimen: Optional[str] = Field(default=None, description="Sample type (e.g. Serum, Whole Blood, Urine)")
    source_page: int = Field(ge=1, description="Page number where finding was located")
    source_evidence: str = Field(description="Exact sentence or table row supporting this fact")
    extraction_method: Literal["DETERMINISTIC_TABLE", "CLINICAL_NLP", "LLM_STRUCTURED"] = Field(
        default="DETERMINISTIC_TABLE"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score for this extraction")
    validation_warnings: List[str] = Field(default_factory=list)


class ClinicalEntity(BaseModel):
    """Named clinical entity (Diagnosis, Symptom, Allergy, Procedure) with evidence context."""
    model_config = ConfigDict(frozen=True)

    text: str = Field(description="Extracted clinical entity name")
    entity_type: Literal["DIAGNOSIS", "SYMPTOM", "ALLERGY", "PROCEDURE", "HISTORICAL_CONDITION"]
    is_negated: bool = Field(default=False, description="True if document explicitly negates entity")
    is_uncertain: bool = Field(default=False, description="True if marked possible/suspected/rule-out")
    temporality: Literal["CURRENT", "PAST", "FAMILY", "UNKNOWN"] = Field(default="CURRENT")
    source_evidence: str = Field(description="Supporting sentence from report")
    source_page: int = Field(ge=1)


class MedicationEntity(BaseModel):
    """Extracted medication statement."""
    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Reported medication name")
    dosage: Optional[str] = Field(default=None, description="Reported strength/dose (e.g. '500 mg')")
    route: Optional[str] = Field(default=None, description="Route (e.g. 'PO', 'IV')")
    frequency: Optional[str] = Field(default=None, description="Frequency (e.g. 'BID', 'daily')")
    is_active: bool = Field(default=True, description="True if current medication, False if discontinued/past")
    source_evidence: str
    source_page: int = Field(ge=1)


class DocumentClassificationResult(BaseModel):
    """Classification of medical document structure and context."""
    model_config = ConfigDict(frozen=True)

    category: str = Field(description="Standard clinical report category (e.g. BIOCHEMISTRY, CBC, DISCHARGE_SUMMARY)")
    confidence: float = Field(ge=0.0, le=1.0)
    detected_language: str = Field(description="Primary ISO language code (e.g. 'en', 'hi', 'mr')")
    secondary_languages: List[str] = Field(default_factory=list)
    is_multilingual: bool = Field(default=False)
    evidence_spans: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ExtractedClinicalData(BaseModel):
    """Comprehensive structured clinical dataset extracted from approved document."""
    model_config = ConfigDict(frozen=True)

    schema_version: str = Field(default="1.0")
    document_id: str
    tenant_id: str
    classification: DocumentClassificationResult
    observations: List[ClinicalObservation] = Field(default_factory=list)
    entities: List[ClinicalEntity] = Field(default_factory=list)
    medications: List[MedicationEntity] = Field(default_factory=list)
    extraction_quality_score: float = Field(ge=0.0, le=1.0)
    review_required: bool = Field(default=False)
    review_reasons: List[str] = Field(default_factory=list)


class Citation(BaseModel):
    """Grounding citation linking generated explanations to verified document passages."""
    model_config = ConfigDict(frozen=True)

    citation_id: str
    source_page: int = Field(ge=1)
    section_name: Optional[str] = None
    evidence_text: str = Field(description="Exact verbatim excerpt from approved source document")
    relevance_score: float = Field(default=1.0)


class KeyFindingExplanation(BaseModel):
    """Layperson-accessible explanation of an individual finding."""
    model_config = ConfigDict(frozen=True)

    finding_title: str
    status: Literal["NORMAL", "ATTENTION", "INFORMATIONAL"]
    lay_explanation: str
    source_citations: List[str] = Field(description="References to Citation IDs")


class GroundedExplanation(BaseModel):
    """Grounded, patient-friendly explanation in the user's preferred language."""
    model_config = ConfigDict(frozen=True)

    explanation_id: str
    document_id: str
    target_language: str = Field(description="ISO code of explanation language ('en', 'hi', 'mr')")
    summary: str = Field(description="Accessible high-level overview of the report")
    key_findings: List[KeyFindingExplanation] = Field(default_factory=list)
    educational_context: str = Field(description="General health educational context clearly distinguished from source facts")
    disclaimer: str = Field(
        default="This explanation is educational and does not constitute medical diagnosis or advice. Please consult your physician."
    )
    citations: List[Citation] = Field(default_factory=list)
    insufficient_evidence: bool = Field(default=False)
    review_warnings: List[str] = Field(default_factory=list)


class QuestionAnswerRequest(BaseModel):
    """Request for grounded document Q&A."""
    model_config = ConfigDict(frozen=True)

    question: str = Field(min_length=3, max_length=1000)
    target_language: Optional[str] = Field(default="en")


class QuestionAnswerResponse(BaseModel):
    """Response for grounded document Q&A."""
    model_config = ConfigDict(frozen=True)

    document_id: str
    question: str
    answer: str
    target_language: str
    status: Literal["ANSWERED", "INSUFFICIENT_EVIDENCE", "RESTRICTED_QUERY"]
    citations: List[Citation] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class TranslationRequest(BaseModel):
    """Request to translate verified clinical educational content."""
    model_config = ConfigDict(frozen=True)

    text: str = Field(min_length=1)
    source_language: str = Field(default="en")
    target_language: str = Field(description="Target ISO code ('en', 'hi', 'mr')")
    preserve_medical_terms: bool = Field(default=True)


class TranslationResponse(BaseModel):
    """Translation response with terminology protection metadata."""
    model_config = ConfigDict(frozen=True)

    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    preserved_terms: List[str] = Field(default_factory=list)
    quality_score: float = Field(default=1.0)
