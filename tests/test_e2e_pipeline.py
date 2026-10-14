"""
End-to-end integration tests for complete clinical document processing pipelines:
- Digital PDF intake, extraction, deidentification, validation, retrieval, deletion.
- Scanned raster image intake with Tesseract OCR fallback.
"""

from fastapi.testclient import TestClient


def test_e2e_digital_pdf_pipeline(client, auth_headers, synthetic_pdf_bytes):
    # 1. Upload digital PDF
    files = {"file": ("discharge_summary.pdf", synthetic_pdf_bytes, "application/pdf")}
    upload_res = client.post("/api/v1/documents", headers=auth_headers, files=files)
    assert upload_res.status_code == 201
    upload_data = upload_res.json()
    doc_id = upload_data["document_id"]
    assert upload_data["status"] == "APPROVED"
    assert "sha256_digest" in upload_data

    # 2. Query status
    status_res = client.get(f"/api/v1/documents/{doc_id}/status", headers=auth_headers)
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["status"] == "APPROVED"
    assert status_data["pages_processed"] == 1

    # 3. Retrieve verified approved result
    result_res = client.get(f"/api/v1/documents/{doc_id}/result", headers=auth_headers)
    assert result_res.status_code == 200
    result_data = result_res.json()

    assert result_data["document_id"] == doc_id
    assert result_data["processing_status"] == "APPROVED"
    assert result_data["quality"]["clinical_content_preserved"] is True
    assert result_data["quality"]["residual_identifiers_detected"] == 0

    clinical_text = result_data["clinical_content"]["text"]

    # Verify patient identifiers are de-identified
    assert "Johnathan Doe" not in clinical_text
    assert "MRN-8849201" not in clinical_text
    assert "4589 1234 5678" not in clinical_text
    assert "+91-9876543210" not in clinical_text
    assert "j.doe.patient@healthcare.example.org" not in clinical_text

    # Verify clinical terms and laboratory results are preserved
    assert "Type 2 Diabetes" in clinical_text
    assert "HbA1c: 8.4%" in clinical_text
    assert "Metformin" in clinical_text
    assert "135/85 mmHg" in clinical_text

    # Verify structured clinical sections parsed
    sections = result_data["clinical_content"]["sections"]
    section_titles = [s["title"] for s in sections]
    assert any("diabetes" in s["content"].lower() or "metformin" in s["content"].lower() for s in sections)

    # 4. Delete document
    del_res = client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True

    # 5. Subsequent retrieval returns 404
    after_res = client.get(f"/api/v1/documents/{doc_id}/result", headers=auth_headers)
    assert after_res.status_code == 404


def test_e2e_scanned_image_ocr_pipeline(client, auth_headers, synthetic_image_bytes):
    # Upload PNG medical scan
    files = {"file": ("lab_scan.png", synthetic_image_bytes, "image/png")}
    upload_res = client.post("/api/v1/documents", headers=auth_headers, files=files)
    assert upload_res.status_code == 201
    upload_data = upload_res.json()
    doc_id = upload_data["document_id"]
    assert upload_data["status"] == "APPROVED"

    # Retrieve approved result
    result_res = client.get(f"/api/v1/documents/{doc_id}/result", headers=auth_headers)
    assert result_res.status_code == 200
    result_data = result_res.json()

    assert "image_direct_ocr" in result_data["extraction"]["methods_used"]
    clinical_text = result_data["clinical_content"]["text"]

    # OCR text should have removed patient identifiers and preserved lab values
    assert "Alice Johnson" not in clinical_text
    assert "HSP-99214" not in clinical_text
    assert "Diabetes" in clinical_text or "HbA1c" in clinical_text

    # Cleanup
    client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers)
