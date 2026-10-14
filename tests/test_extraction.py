"""
Unit tests for text extraction, selective OCR fallback, and provenance tracking.
"""

from pathlib import Path
import fitz

from clinivara.extraction.extractor import document_extractor
from clinivara.storage.storage_manager import storage_manager


def test_digital_pdf_extraction(tmp_path, synthetic_pdf_bytes):
    tenant_id = "test_tenant"
    doc_id = "test_doc_pdf_1"
    corr_id = "corr_123"

    # Save to Boundary A
    pdf_path = storage_manager.save_original_document(
        tenant_id=tenant_id,
        document_id=doc_id,
        extension=".pdf",
        content=synthetic_pdf_bytes,
    )

    result = document_extractor.extract_document(
        tenant_id=tenant_id,
        document_id=doc_id,
        correlation_id=corr_id,
        file_path=pdf_path,
    )

    assert result.status == "COMPLETED"
    assert result.total_pages == 1
    assert result.pages[0].method == "DIGITAL_TEXT"
    assert "Type 2 Diabetes" in result.pages[0].text
    assert "Metformin" in result.pages[0].text
    assert "embedded_digital_text" in result.methods_used

    # Cleanup
    storage_manager.delete_document_record(tenant_id, doc_id)


def test_raster_image_ocr_extraction(tmp_path, synthetic_image_bytes):
    tenant_id = "test_tenant"
    doc_id = "test_doc_img_1"
    corr_id = "corr_456"

    img_path = storage_manager.save_original_document(
        tenant_id=tenant_id,
        document_id=doc_id,
        extension=".png",
        content=synthetic_image_bytes,
    )

    result = document_extractor.extract_document(
        tenant_id=tenant_id,
        document_id=doc_id,
        correlation_id=corr_id,
        file_path=img_path,
    )

    assert result.status == "COMPLETED"
    assert result.total_pages == 1
    assert result.pages[0].method == "IMAGE_DIRECT"
    assert "Diabetes" in result.pages[0].text or "HbA1c" in result.pages[0].text
    assert result.pages[0].ocr_confidence is not None

    # Cleanup
    storage_manager.delete_document_record(tenant_id, doc_id)
