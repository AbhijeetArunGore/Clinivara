"""
Release gate enforcing fail-closed privacy verification.

Strict invariant:
Only documents with 0 residual identifiers, verified clinical preservation,
and complete Pydantic contract validation may achieve APPROVED status.
"""

from typing import Any, Dict, List, Literal, Tuple
from clinivara.audit.audit_logger import audit_logger
from clinivara.core.config import settings
from clinivara.extraction.models import ExtractionResult
from clinivara.normalization.text_cleaner import text_cleaner
from clinivara.schemas.approved_output import (
    ApprovedDocumentOutput,
    ClinicalContent,
    DeidentificationMetadata,
    ExtractionMetadata,
    QualityMetadata,
)
from clinivara.storage.storage_manager import storage_manager
from clinivara.validation.preservation_checker import preservation_checker
from clinivara.validation.residual_detector import residual_scanner


class ReleaseGate:
    """Enforces the release invariant: Original -> Processing -> Validation -> Approved."""

    @staticmethod
    def evaluate_and_commit(
        tenant_id: str,
        document_id: str,
        correlation_id: str,
        raw_text: str,
        deidentified_text: str,
        extraction_result: ExtractionResult,
        transformed_counts: Dict[str, int],
    ) -> Tuple[Literal["APPROVED", "REJECTED", "REVIEW_REQUIRED"], List[str], Dict[str, Any]]:
        """
        Evaluate de-identified text against independent second-pass checks and schema constraints.
        Returns:
            (decision_status, warnings_list, metrics_dict)
        """
        warnings: List[str] = []

        try:
            # 1. Independent Second-Pass Residual Scanner
            residual_count, residual_warnings = residual_scanner.scan_for_residuals(deidentified_text)
            warnings.extend(residual_warnings)

            # 2. Clinical Preservation Check
            preserved, preservation_warnings = preservation_checker.check_preservation(
                raw_text, deidentified_text
            )
            warnings.extend(preservation_warnings)

            # 3. Parse Clinical Sections
            sections = text_cleaner.extract_sections(deidentified_text)

            # 4. Determine Release Status (Fail-Closed)
            if residual_count > 0:
                decision: Literal["APPROVED", "REJECTED", "REVIEW_REQUIRED"] = "REJECTED"
                val_status: Literal["PASSED", "FAILED", "REVIEW_REQUIRED"] = "FAILED"
            elif not preserved and len(preservation_warnings) > 2:
                decision = "REVIEW_REQUIRED"
                val_status = "REVIEW_REQUIRED"
            else:
                decision = "APPROVED"
                val_status = "PASSED"

            # 5. If APPROVED, construct and validate strict ApprovedDocumentOutput model
            if decision == "APPROVED":
                output_model = ApprovedDocumentOutput(
                    schema_version="1.0",
                    document_id=document_id,
                    tenant_id=tenant_id,
                    processing_status="APPROVED",
                    extraction=ExtractionMetadata(
                        status=extraction_result.status,
                        pages_processed=len(extraction_result.pages),
                        methods_used=extraction_result.methods_used,
                        warnings=extraction_result.warnings,
                    ),
                    deidentification=DeidentificationMetadata(
                        status="COMPLETED",
                        policy_version=settings.deid_policy_version,
                        validation_status=val_status,
                        transformed_entity_counts=transformed_counts,
                    ),
                    clinical_content=ClinicalContent(
                        text=deidentified_text,
                        sections=sections,
                    ),
                    quality=QualityMetadata(
                        schema_valid=True,
                        clinical_content_preserved=preserved,
                        residual_identifiers_detected=residual_count,
                    ),
                )

                # Commit to Boundary C Approved Storage
                storage_manager.save_approved_output(tenant_id, document_id, output_model)

            # 6. Update Document Metadata
            meta = storage_manager.get_document_metadata(tenant_id, document_id) or {}
            meta.update({
                "status": decision,
                "stage": f"RELEASE_DECISION_{decision}",
                "residual_count": residual_count,
                "clinical_preserved": preserved,
                "warnings": warnings,
            })
            storage_manager.save_document_metadata(tenant_id, document_id, meta)

            # 7. Audit Event
            event_type = "RELEASE_APPROVED" if decision == "APPROVED" else (
                "RELEASE_REJECTED" if decision == "REJECTED" else "RELEASE_REVIEW_REQUIRED"
            )
            audit_logger.record_event(
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                event_type=event_type,
                status="SUCCESS" if decision == "APPROVED" else "WARNING",
                document_id=document_id,
                details={
                    "decision": decision,
                    "residual_identifiers": residual_count,
                    "clinical_preserved": preserved,
                    "warnings_count": len(warnings),
                },
            )

            metrics = {
                "decision": decision,
                "residual_count": residual_count,
                "clinical_preserved": preserved,
                "warnings_count": len(warnings),
            }
            return decision, warnings, metrics

        except Exception as e:
            # Absolute Fail-Closed invariant
            decision = "REJECTED"
            warnings.append(f"Validation system exception: {type(e).__name__}")
            meta = storage_manager.get_document_metadata(tenant_id, document_id) or {}
            meta.update({
                "status": "REJECTED",
                "stage": "VALIDATION_EXCEPTION",
                "warnings": warnings,
            })
            storage_manager.save_document_metadata(tenant_id, document_id, meta)

            audit_logger.record_event(
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                event_type="RELEASE_REJECTED",
                status="FAILURE",
                document_id=document_id,
                details={"reason": "Validation Exception", "error": type(e).__name__},
            )

            return "REJECTED", warnings, {"decision": "REJECTED", "error": type(e).__name__}


release_gate = ReleaseGate()
