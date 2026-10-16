"""
Deterministic, typed AI Orchestration Workflow State Machine.
Executes end-to-end clinical document analysis on Boundary C approved outputs.
Strictly isolates data, audits facts against source evidence, and supports English, Hindi, and Marathi.
"""

from enum import Enum
import time
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from clinivara.ai.guardrails.consistency_auditor import ClinicalConsistencyAuditor
from clinivara.ai.guardrails.injection_guard import PromptInjectionGuard
from clinivara.ai.prompts.registry import prompt_registry
from clinivara.ai.providers import get_llm_provider
from clinivara.clinical.document_classifier import ClinicalDocumentClassifier
from clinivara.clinical.extraction.extractor import ClinicalExtractor
from clinivara.multilingual.language_detection import LanguageDetector
from clinivara.multilingual.translation import MultilingualTranslator
from clinivara.schemas.ai import (
    Citation,
    ClinicalObservation,
    DocumentClassificationResult,
    ExtractedClinicalData,
    GroundedExplanation,
    KeyFindingExplanation,
)
from clinivara.schemas.approved_output import ApprovedDocumentOutput
from clinivara.storage.storage_manager import storage_manager


class WorkflowState(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    EXTRACTED = "EXTRACTED"
    VALIDATION_PENDING = "VALIDATION_PENDING"
    APPROVED = "APPROVED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


# Allowed state transitions
PERMITTED_TRANSITIONS = {
    WorkflowState.QUEUED: [WorkflowState.PROCESSING, WorkflowState.FAILED],
    WorkflowState.PROCESSING: [WorkflowState.EXTRACTED, WorkflowState.PARTIAL, WorkflowState.FAILED],
    WorkflowState.EXTRACTED: [WorkflowState.VALIDATION_PENDING, WorkflowState.FAILED],
    WorkflowState.VALIDATION_PENDING: [WorkflowState.APPROVED, WorkflowState.PARTIAL, WorkflowState.FAILED],
    WorkflowState.APPROVED: [],
    WorkflowState.PARTIAL: [],
    WorkflowState.FAILED: [],
}


class StageTiming(BaseModel):
    stage_name: str
    duration_ms: float


class WorkflowResult(BaseModel):
    """Complete typed execution record of the AI document analysis pipeline."""
    model_config = ConfigDict(frozen=True)

    workflow_id: str
    document_id: str
    tenant_id: str
    status: WorkflowState
    state_history: List[str]
    classification: Optional[DocumentClassificationResult] = None
    clinical_data: Optional[ExtractedClinicalData] = None
    explanation: Optional[GroundedExplanation] = None
    timings: List[StageTiming] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class ClinicalAnalysisWorkflow:
    """Orchestrates secure clinical document understanding pipeline."""

    def __init__(self):
        self.language_detector = LanguageDetector()
        self.document_classifier = ClinicalDocumentClassifier()
        self.clinical_extractor = ClinicalExtractor()
        self.consistency_auditor = ClinicalConsistencyAuditor()
        self.injection_guard = PromptInjectionGuard()
        self.translator = MultilingualTranslator()
        self.llm_provider = get_llm_provider()

    def _transition(self, current_state: WorkflowState, next_state: WorkflowState, history: List[str]) -> WorkflowState:
        if next_state not in PERMITTED_TRANSITIONS.get(current_state, []):
            raise ValueError(f"Illegal state transition from {current_state} to {next_state}")
        history.append(f"{current_state} -> {next_state}")
        return next_state

    def execute(
        self,
        tenant_id: str,
        document_id: str,
        target_language: str = "en",
        approved_doc: Optional[ApprovedDocumentOutput] = None,
    ) -> WorkflowResult:
        """
        Execute analysis workflow on approved document output.
        """
        history: List[str] = []
        timings: List[StageTiming] = []
        warnings: List[str] = []
        errors: List[str] = []
        state = WorkflowState.QUEUED
        history.append(f"INITIAL: {state}")

        # 1. State: QUEUED -> PROCESSING
        t0 = time.perf_counter()
        state = self._transition(state, WorkflowState.PROCESSING, history)

        try:
            # Load approved document if not passed directly
            if not approved_doc:
                approved_doc = storage_manager.get_approved_output(tenant_id, document_id)

            document_text = approved_doc.clinical_content.text
            t_load = (time.perf_counter() - t0) * 1000
            timings.append(StageTiming(stage_name="load_approved_output", duration_ms=round(t_load, 2)))

            # Check injection guard
            is_safe, inj_matches = self.injection_guard.inspect_text(document_text)
            if not is_safe:
                warnings.append(f"Prompt injection patterns detected in document: {inj_matches}")
            sanitized_text = self.injection_guard.sanitize_delimiters(document_text)

            # 2. Language & Script Detection
            t_start = time.perf_counter()
            lang_detect = self.language_detector.detect_language(sanitized_text)
            timings.append(StageTiming(stage_name="language_detection", duration_ms=round((time.perf_counter() - t_start) * 1000, 2)))

            # 3. Document Classification
            t_start = time.perf_counter()
            classification = self.document_classifier.classify(sanitized_text)
            timings.append(StageTiming(stage_name="document_classification", duration_ms=round((time.perf_counter() - t_start) * 1000, 2)))

            # 4. Clinical Extraction
            t_start = time.perf_counter()
            extracted_data = self.clinical_extractor.extract(
                document_id=document_id,
                tenant_id=tenant_id,
                approved_text=sanitized_text,
                page_count=approved_doc.extraction.pages_processed,
            )
            timings.append(StageTiming(stage_name="clinical_extraction", duration_ms=round((time.perf_counter() - t_start) * 1000, 2)))

            state = self._transition(state, WorkflowState.EXTRACTED, history)

            # 5. Extraction Validation & Consistency Audit
            t_start = time.perf_counter()
            state = self._transition(state, WorkflowState.VALIDATION_PENDING, history)

            audit_res = self.consistency_auditor.audit_observations(
                observations=extracted_data.observations,
                approved_source_text=sanitized_text,
            )
            for finding in audit_res.findings:
                if finding.severity == "CRITICAL":
                    errors.append(f"Extraction audit critical: {finding.description}")
                else:
                    warnings.append(f"Extraction audit warning: {finding.description}")

            timings.append(StageTiming(stage_name="extraction_audit", duration_ms=round((time.perf_counter() - t_start) * 1000, 2)))

            # 6. Patient-Friendly Explanation Generation
            t_start = time.perf_counter()
            citations: List[Citation] = []
            for idx, obs in enumerate(extracted_data.observations[:10], start=1):
                citations.append(
                    Citation(
                        citation_id=f"cit-{idx}",
                        source_page=obs.source_page,
                        section_name="LABORATORY RESULTS",
                        evidence_text=obs.source_evidence,
                        relevance_score=1.0,
                    )
                )

            # Formulate prompt for LLM provider or mock
            explanation_prompt = prompt_registry.get_prompt("D_PATIENT_EXPLANATION").user_template.format(
                target_language=target_language,
                validated_clinical_json=extracted_data.model_dump_json(),
                retrieved_evidence="\n".join([f"[{c.citation_id}] {c.evidence_text}" for c in citations]),
            )

            explanation = self.llm_provider.generate_structured(
                prompt=explanation_prompt,
                response_model=GroundedExplanation,
                system_prompt=prompt_registry.get_prompt("D_PATIENT_EXPLANATION").system_prompt,
            )
            timings.append(StageTiming(stage_name="explanation_generation", duration_ms=round((time.perf_counter() - t_start) * 1000, 2)))

            # 7. Explanation Audit
            t_start = time.perf_counter()
            exp_audit = self.consistency_auditor.audit_explanation(explanation, sanitized_text)
            for finding in exp_audit.findings:
                if finding.severity == "CRITICAL":
                    errors.append(f"Explanation audit critical: {finding.description}")
                else:
                    warnings.append(f"Explanation audit warning: {finding.description}")
            timings.append(StageTiming(stage_name="explanation_audit", duration_ms=round((time.perf_counter() - t_start) * 1000, 2)))

            # Final status evaluation
            if errors:
                final_state = self._transition(state, WorkflowState.PARTIAL, history)
            else:
                final_state = self._transition(state, WorkflowState.APPROVED, history)

            result = WorkflowResult(
                workflow_id=f"wf-{int(time.time()*1000)}",
                document_id=document_id,
                tenant_id=tenant_id,
                status=final_state,
                state_history=history,
                classification=classification,
                clinical_data=extracted_data,
                explanation=explanation,
                timings=timings,
                warnings=warnings,
                errors=errors,
            )

            # Persist derived metadata safely (Non-identifying summary)
            meta = storage_manager.get_document_metadata(tenant_id, document_id) or {}
            meta["ai_analysis"] = {
                "workflow_id": result.workflow_id,
                "status": result.status.value,
                "category": classification.category,
                "detected_language": lang_detect.detected_language,
                "observations_count": len(extracted_data.observations),
                "is_abnormal": any(o.is_abnormal for o in extracted_data.observations),
                "target_language": target_language,
            }
            storage_manager.save_document_metadata(tenant_id, document_id, meta)

            return result

        except Exception as exc:
            errors.append(f"Workflow execution failure: {str(exc)}")
            try:
                state = self._transition(state, WorkflowState.FAILED, history)
            except Exception:
                history.append(f"{state} -> {WorkflowState.FAILED}")
                state = WorkflowState.FAILED

            return WorkflowResult(
                workflow_id=f"wf-{int(time.time()*1000)}",
                document_id=document_id,
                tenant_id=tenant_id,
                status=state,
                state_history=history,
                timings=timings,
                warnings=warnings,
                errors=errors,
            )
