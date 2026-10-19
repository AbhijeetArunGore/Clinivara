"""
Deterministic Mock LLM Provider for offline testing, CI/CD, and non-external LLM operations.
Guarantees schema-compliant responses without network access or third-party API dependencies.
"""

import re
from typing import Any

from pydantic import BaseModel

from clinivara.ai.providers.base import LLMProvider
from clinivara.schemas.ai import (
    Citation,
    ClinicalObservation,
    DocumentClassificationResult,
    ExtractedClinicalData,
    GroundedExplanation,
    KeyFindingExplanation,
    QuestionAnswerResponse,
    ReferenceRange,
    TranslationResponse,
)


class MockLLMProvider(LLMProvider):
    """Deterministic mock LLM provider for zero-cost offline validation."""

    def __init__(self, mock_language: str = "en"):
        self.mock_language = mock_language

    def health_check(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "provider": "mock",
            "offline_mode": True,
            "capabilities": ["classification", "extraction", "explanation", "qna", "translation"],
        }

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ) -> str:
        """Generate deterministic text responses based on prompt keywords."""
        prompt_lower = prompt.lower()
        if "audit" in prompt_lower or "consistency" in prompt_lower:
            return "AUDIT_RESULT: PASS. All claims supported by source evidence. Zero altered values or lost negations."
        if "translate" in prompt_lower:
            return "This is a deterministic mock translation preserving clinical units and numeric precision."
        return "Deterministic educational explanation grounded strictly in the provided medical report."

    def generate_structured(
        self,
        prompt: str,
        response_model: type[BaseModel],
        system_prompt: str | None = None,
        temperature: float = 0.0,
    ) -> BaseModel:
        """Generate schema-conforming Pydantic models deterministically."""
        if issubclass(response_model, DocumentClassificationResult):
            return self._mock_classification(prompt)
        elif issubclass(response_model, ExtractedClinicalData):
            return self._mock_extraction(prompt)
        elif issubclass(response_model, GroundedExplanation):
            return self._mock_explanation(prompt)
        elif issubclass(response_model, QuestionAnswerResponse):
            return self._mock_qna(prompt)
        elif issubclass(response_model, TranslationResponse):
            return self._mock_translation(prompt)

        # Generic fallback using response_model fields if custom type requested
        return response_model.model_construct()

    def _mock_classification(self, prompt: str) -> DocumentClassificationResult:
        prompt_lower = prompt.lower()
        category = "UNKNOWN"
        confidence = 0.85
        detected_lang = "en"
        evidence_spans = []

        if any(w in prompt_lower for w in ["hemoglobin", "platelet", "wbc", "rbc", "hematology", "सीबीसी", "रक्त"]):
            category = "HEMATOLOGY_CBC"
            confidence = 0.95
            evidence_spans.append("Detected complete blood count test parameters")
        elif any(
            w in prompt_lower
            for w in ["glucose", "creatinine", "urea", "bilirubin", "lipid", "cholesterol", "बायोकेमिस्ट्री"]
        ):
            category = "BIOCHEMISTRY_METABOLIC"
            confidence = 0.92
            evidence_spans.append("Detected metabolic panel parameters")
        elif any(w in prompt_lower for w in ["discharge", "admission", "hospital", "डिस्चार्ज"]):
            category = "DISCHARGE_SUMMARY"
            confidence = 0.90
            evidence_spans.append("Detected discharge summary clinical structure")

        # Script detection
        if any("\u0900" <= char <= "\u097f" for char in prompt):
            if "आहे" in prompt or "नाही" in prompt or "रुग्ण" in prompt:
                detected_lang = "mr"
            else:
                detected_lang = "hi"

        return DocumentClassificationResult(
            category=category,
            confidence=confidence,
            detected_language=detected_lang,
            secondary_languages=["en"] if detected_lang != "en" else [],
            is_multilingual=detected_lang != "en",
            evidence_spans=evidence_spans or ["Document text matching standard clinical format"],
            warnings=[],
        )

    def _mock_extraction(self, prompt: str) -> ExtractedClinicalData:
        # Simple regex extraction for key synthetic test parameters in prompt
        observations: list[ClinicalObservation] = []

        # Pattern for "TestName: Value Unit (Ref)" or "TestName Value Unit Ref"
        lines = prompt.splitlines()
        for idx, line in enumerate(lines):
            line_str = line.strip()
            # Fast scan for common tests
            for test in ["Hemoglobin", "WBC", "Platelet Count", "Fasting Glucose", "Serum Creatinine", "HbA1c"]:
                if test.lower() in line_str.lower():
                    # Parse numeric value if present
                    val_match = re.search(r"(\d+(?:\.\d+)?)", line_str)
                    val = val_match.group(1) if val_match else "12.0"
                    observations.append(
                        ClinicalObservation(
                            observation_id=f"obs-mock-{idx}",
                            test_name=test,
                            original_test_name=test,
                            normalized_test_name=test,
                            original_value=val,
                            numeric_value=float(val),
                            comparator=None,
                            original_unit="g/dL" if "hemo" in test.lower() else "mg/dL",
                            normalized_unit="g/dL" if "hemo" in test.lower() else "mg/dL",
                            reference_range=ReferenceRange(
                                raw_text="12.0 - 15.0",
                                low=12.0,
                                high=15.0,
                                unit="g/dL" if "hemo" in test.lower() else "mg/dL",
                            ),
                            source_reported_status=None,
                            derived_status="NORMAL",
                            is_abnormal=False,
                            source_page=1,
                            source_evidence=line_str,
                            extraction_method="LLM_STRUCTURED",
                            confidence=0.95,
                        )
                    )

        return ExtractedClinicalData(
            schema_version="1.0",
            document_id="doc-mock-extract",
            tenant_id="tenant-default",
            classification=DocumentClassificationResult(
                category="HEMATOLOGY_CBC",
                confidence=0.95,
                detected_language="en",
                evidence_spans=["Extracted laboratory test observations"],
            ),
            observations=observations,
            entities=[],
            medications=[],
            extraction_quality_score=0.95 if observations else 0.80,
            review_required=False,
        )

    def _mock_explanation(self, prompt: str) -> GroundedExplanation:
        target_lang = "en"
        if "Preferred language: hi" in prompt or "target_language: hi" in prompt:
            target_lang = "hi"
        elif "Preferred language: mr" in prompt or "target_language: mr" in prompt:
            target_lang = "mr"

        # Extract evidence citations from prompt if present
        evidence_match = re.search(r"<evidence>\s*(.*?)\s*</evidence>", prompt, re.DOTALL)
        evidence_lines = (
            [line.strip() for line in evidence_match.group(1).splitlines() if line.strip()] if evidence_match else []
        )

        citations = []
        key_findings = []

        if evidence_lines:
            for idx, eline in enumerate(evidence_lines[:3], start=1):
                clean_line = re.sub(r"^\[cit-\d+\]\s*", "", eline)
                citations.append(
                    Citation(
                        citation_id=f"cit-{idx}",
                        source_page=1,
                        section_name="LABORATORY RESULTS",
                        evidence_text=clean_line,
                        relevance_score=1.0,
                    )
                )
                title = clean_line.split(":")[0].strip() if ":" in clean_line else "Clinical Finding"
                key_findings.append(
                    KeyFindingExplanation(
                        finding_title=title,
                        status="NORMAL",
                        lay_explanation=f"Reported finding: {clean_line}",
                        source_citations=[f"cit-{idx}"],
                    )
                )
        else:
            citations = [
                Citation(
                    citation_id="cit-mock-1",
                    source_page=1,
                    section_name="LABORATORY RESULTS",
                    evidence_text="Hemoglobin 13.5 g/dL (Reference: 12.0 - 15.0 g/dL)",
                    relevance_score=1.0,
                )
            ]
            key_findings = [
                KeyFindingExplanation(
                    finding_title="Hemoglobin",
                    status="NORMAL",
                    lay_explanation="Hemoglobin is within the reported reference range.",
                    source_citations=["cit-mock-1"],
                )
            ]

        if target_lang == "hi":
            summary = "यह एक चिकित्सीय प्रयोगशाला रिपोर्ट है जिसमें निष्कर्ष सामान्य पाए गए हैं।"
            educational_context = "रक्त जांच शरीर के समग्र स्वास्थ्य और चयापचय का आकलन करने में सहायक होती है।"
        elif target_lang == "mr":
            summary = "हा एक वैद्यकीय प्रयोगशाळा तपासणी अहवाल आहे ज्यामध्ये निकाल सामान्य आढळले आहेत."
            educational_context = "रक्त तपासणी शरीराच्या एकूण आरोग्याचे आणि घटकांचे मूल्यमापन करण्यात मदत करते."
        else:
            summary = (
                "This is a medical laboratory report showing findings evaluated against reported reference ranges."
            )
            educational_context = "Laboratory tests evaluate cellular components, enzymes, and metabolic markers to assist healthcare providers."

        return GroundedExplanation(
            explanation_id="exp-mock-1",
            document_id="doc-mock-1",
            target_language=target_lang,
            summary=summary,
            key_findings=key_findings,
            educational_context=educational_context,
            disclaimer="This explanation is educational and does not constitute medical diagnosis or advice. Please consult your physician.",
            citations=citations,
            insufficient_evidence=False,
            review_warnings=[],
        )

    def _mock_qna(self, prompt: str) -> QuestionAnswerResponse:
        # Extract user question from prompt
        q_match = re.search(r"Question:\s*(.*?)\n\n", prompt, re.DOTALL)
        question = q_match.group(1).strip() if q_match else "User Question"

        # Extract evidence text from prompt if present
        evidence_match = re.search(r"<evidence>\s*(.*?)\s*</evidence>", prompt, re.DOTALL)
        evidence_text = evidence_match.group(1).strip() if evidence_match else ""

        # Check sufficiency: if no evidence found or evidence does not contain keywords from question
        q_lower = question.lower()
        if not evidence_text or ("cholesterol" in q_lower and "cholesterol" not in evidence_text.lower()):
            return QuestionAnswerResponse(
                document_id="doc-mock-qna",
                question=question,
                answer="The provided document does not contain sufficient evidence to answer this question.",
                target_language="en",
                status="INSUFFICIENT_EVIDENCE",
                citations=[],
                warnings=["Query pertains to facts not present in approved source document."],
            )

        first_line = evidence_text.splitlines()[0] if evidence_text else "Observation verified."
        citations = [
            Citation(
                citation_id="cit-qna-1",
                source_page=1,
                section_name="OBSERVATIONS",
                evidence_text=first_line,
                relevance_score=0.98,
            )
        ]

        return QuestionAnswerResponse(
            document_id="doc-mock-qna",
            question=question,
            answer=f"Based on the approved document evidence: {first_line}",
            target_language="en",
            status="ANSWERED",
            citations=citations,
            warnings=[],
        )

    def _mock_translation(self, prompt: str) -> TranslationResponse:
        target_lang = "hi" if "target_language: hi" in prompt.lower() else "mr"
        return TranslationResponse(
            original_text="Hemoglobin is 13.5 g/dL which is within normal limits.",
            translated_text="हीमोग्लोबिन 13.5 g/dL है जो सामान्य सीमा के भीतर है।"
            if target_lang == "hi"
            else "हिमोग्लोबिन 13.5 g/dL आहे जे सामान्य मर्यादेत आहे.",
            source_language="en",
            target_language=target_lang,
            preserved_terms=["Hemoglobin", "13.5", "g/dL"],
            quality_score=0.98,
        )
