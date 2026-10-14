"""
Unit tests for the independent release gate, residual scanner, and fail-closed privacy enforcement.
"""

import pytest
from clinivara.core.errors import UnapprovedOutputAccessError
from clinivara.extraction.models import ExtractionResult, PageExtraction
from clinivara.schemas.approved_output import (
    ApprovedDocumentOutput,
    ClinicalContent,
    DeidentificationMetadata,
    ExtractionMetadata,
    QualityMetadata,
)
from clinivara.storage.storage_manager import storage_manager
from clinivara.validation.release_gate import release_gate
from clinivara.validation.residual_detector import residual_scanner


def test_residual_scanner_detection():
    clean_text = "Patient: [NAME], Diagnosis: Type 2 Diabetes, Lab: HbA1c 7.5%"
    count, warnings = residual_scanner.scan_for_residuals(clean_text)
    assert count == 0
    assert len(warnings) == 0

    leaked_text = "Patient: [NAME], Contact phone: 9876543210, Email: leak@hospital.com"
    count, warnings = residual_scanner.scan_for_residuals(leaked_text)
    assert count >= 2
    assert any("RESIDUAL_EMAIL" in w for w in warnings)
    assert any("RESIDUAL_PHONE" in w for w in warnings)


def test_release_gate_approval():
    tenant_id = "tenant_gate_1"
    doc_id = "doc_gate_approved"
    corr_id = "corr_gate_1"

    raw_text = "Patient: Alice Smith, HbA1c: 8.1%, Metformin 500 mg"
    clean_deid_text = "Patient: [NAME], HbA1c: 8.1%, Metformin 500 mg"

    ext_res = ExtractionResult(
        document_id=doc_id,
        tenant_id=tenant_id,
        correlation_id=corr_id,
        pages=[PageExtraction(
            page_number=1,
            method="DIGITAL_TEXT",
            text=raw_text,
            character_count=len(raw_text),
            word_count=len(raw_text.split()),
        )],
        methods_used=["embedded_digital_text"],
        total_pages=1,
        status="COMPLETED",
    )

    decision, warnings, metrics = release_gate.evaluate_and_commit(
        tenant_id=tenant_id,
        document_id=doc_id,
        correlation_id=corr_id,
        raw_text=raw_text,
        deidentified_text=clean_deid_text,
        extraction_result=ext_res,
        transformed_counts={"NAME": 1},
    )

    assert decision == "APPROVED"
    assert metrics["residual_count"] == 0

    # Retrieve approved output
    approved_output = storage_manager.get_approved_output(tenant_id, doc_id)
    assert approved_output.document_id == doc_id
    assert approved_output.processing_status == "APPROVED"

    # Cleanup
    storage_manager.delete_document_record(tenant_id, doc_id)


def test_release_gate_fail_closed_rejection():
    tenant_id = "tenant_gate_2"
    doc_id = "doc_gate_rejected"
    corr_id = "corr_gate_2"

    raw_text = "Patient: Alice Smith, Phone: 9876543210"
    # Unredacted phone remains in output
    leaked_deid_text = "Patient: [NAME], Phone: 9876543210"

    ext_res = ExtractionResult(
        document_id=doc_id,
        tenant_id=tenant_id,
        correlation_id=corr_id,
        pages=[PageExtraction(
            page_number=1,
            method="DIGITAL_TEXT",
            text=raw_text,
            character_count=len(raw_text),
            word_count=len(raw_text.split()),
        )],
        methods_used=["embedded_digital_text"],
        total_pages=1,
        status="COMPLETED",
    )

    decision, warnings, metrics = release_gate.evaluate_and_commit(
        tenant_id=tenant_id,
        document_id=doc_id,
        correlation_id=corr_id,
        raw_text=raw_text,
        deidentified_text=leaked_deid_text,
        extraction_result=ext_res,
        transformed_counts={"NAME": 1},
    )

    assert decision == "REJECTED"
    assert metrics["residual_count"] > 0

    # Downstream retrieval must be blocked with UnapprovedOutputAccessError
    with pytest.raises(UnapprovedOutputAccessError):
        storage_manager.get_approved_output(tenant_id, doc_id)

    # Cleanup
    storage_manager.delete_document_record(tenant_id, doc_id)


def test_approved_output_model_invariant_enforcement():
    # Attempting to construct an ApprovedDocumentOutput with residual identifiers detected must fail
    with pytest.raises(ValueError):
        ApprovedDocumentOutput(
            schema_version="1.0",
            document_id="doc_invalid",
            tenant_id="tenant_x",
            processing_status="APPROVED",
            extraction=ExtractionMetadata(status="COMPLETED", pages_processed=1, methods_used=["digital_text"]),
            deidentification=DeidentificationMetadata(status="COMPLETED", policy_version="1.0", validation_status="PASSED"),
            clinical_content=ClinicalContent(text="Patient: [NAME]", sections=[]),
            quality=QualityMetadata(schema_valid=True, clinical_content_preserved=True, residual_identifiers_detected=1),
        )
