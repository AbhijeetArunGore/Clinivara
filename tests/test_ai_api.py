"""
End-to-End API integration tests for /api/v1/ai endpoints:
- Discovery: health, capabilities, languages.
- Extraction & Clinical Data.
- Grounded explanation (English, Hindi, Marathi).
- RAG question answering.
- Terminology-safe translation.
- Security boundaries (401 Unauthorized, 404 Not Found, 409 Document Not Ready).
"""

import pytest
from fastapi.testclient import TestClient

from clinivara.main import app
from clinivara.schemas.approved_output import (
    ApprovedDocumentOutput,
    ClinicalContent,
    DeidentificationMetadata,
    ExtractionMetadata,
    QualityMetadata,
)
from clinivara.storage.storage_manager import storage_manager

client = TestClient(app)
VALID_API_KEY = "clinivara-dev-client-key-alpha-9921"
TENANT_ID = "clinic_default_tenant"


@pytest.fixture(autouse=True)
def setup_test_approved_document():
    doc_id = "test_api_doc_99"
    text = (
        "COMPLETE BLOOD COUNT REPORT\n"
        "Hemoglobin: 13.8 g/dL (Reference: 12.0 - 15.5 g/dL)\n"
        "Platelet Count: 240000 /cumm (Reference: 150000 - 450000 /cumm)\n"
        "WBC Count: 6800 /cumm\n"
        "Impression: Normal hematology."
    )
    approved_doc = ApprovedDocumentOutput(
        document_id=doc_id,
        tenant_id=TENANT_ID,
        processing_status="APPROVED",
        extraction=ExtractionMetadata(status="COMPLETED", pages_processed=1, methods_used=["text"]),
        deidentification=DeidentificationMetadata(status="COMPLETED", validation_status="PASSED"),
        clinical_content=ClinicalContent(text=text, sections=[]),
        quality=QualityMetadata(schema_valid=True, clinical_content_preserved=True, residual_identifiers_detected=0),
    )
    storage_manager.save_approved_output(TENANT_ID, doc_id, approved_doc)
    yield doc_id
    storage_manager.delete_document_record(TENANT_ID, doc_id)


def test_ai_health_endpoint():
    resp = client.get("/api/v1/ai/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["subsystem"] == "ai_data_science"
    assert "supported_languages" in data


def test_ai_capabilities_endpoint():
    resp = client.get("/api/v1/ai/capabilities")
    assert resp.status_code == 200
    data = resp.json()
    assert "clinical_extraction" in data
    assert "multilingual_support" in data
    assert "grounded_rag" in data


def test_ai_languages_endpoint():
    resp = client.get("/api/v1/ai/languages")
    assert resp.status_code == 200
    languages = resp.json()
    assert len(languages) >= 3
    lang_codes = [l["code"] for l in languages]
    assert "en" in lang_codes
    assert "hi" in lang_codes
    assert "mr" in lang_codes


def test_clinical_extract_authenticated(setup_test_approved_document):
    doc_id = setup_test_approved_document
    resp = client.post(
        f"/api/v1/ai/documents/{doc_id}/extract",
        headers={"X-API-Key": VALID_API_KEY},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "APPROVED"
    assert data["classification"]["category"] == "HEMATOLOGY_CBC"
    assert len(data["clinical_data"]["observations"]) >= 2


def test_get_clinical_data_authenticated(setup_test_approved_document):
    doc_id = setup_test_approved_document
    resp = client.get(
        f"/api/v1/ai/documents/{doc_id}/clinical-data",
        headers={"X-API-Key": VALID_API_KEY},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["observations"]) >= 2
    assert any("Hemoglobin" in o["test_name"] for o in data["observations"])


def test_explain_document_trilingual(setup_test_approved_document):
    doc_id = setup_test_approved_document
    
    # 1. English
    resp_en = client.post(
        f"/api/v1/ai/documents/{doc_id}/explain",
        json={"target_language": "en"},
        headers={"X-API-Key": VALID_API_KEY},
    )
    assert resp_en.status_code == 200
    assert resp_en.json()["target_language"] == "en"
    assert len(resp_en.json()["citations"]) > 0

    # 2. Hindi
    resp_hi = client.post(
        f"/api/v1/ai/documents/{doc_id}/explain",
        json={"target_language": "hi"},
        headers={"X-API-Key": VALID_API_KEY},
    )
    assert resp_hi.status_code == 200
    assert resp_hi.json()["target_language"] == "hi"

    # 3. Marathi
    resp_mr = client.post(
        f"/api/v1/ai/documents/{doc_id}/explain",
        json={"target_language": "mr"},
        headers={"X-API-Key": VALID_API_KEY},
    )
    assert resp_mr.status_code == 200
    assert resp_mr.json()["target_language"] == "mr"


def test_rag_question_answering_endpoint(setup_test_approved_document):
    doc_id = setup_test_approved_document

    # Question with evidence
    resp = client.post(
        f"/api/v1/ai/documents/{doc_id}/questions",
        json={"question": "What is the hemoglobin level?", "target_language": "en"},
        headers={"X-API-Key": VALID_API_KEY},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ANSWERED"
    assert len(data["citations"]) > 0

    # Question with insufficient evidence
    resp_insuf = client.post(
        f"/api/v1/ai/documents/{doc_id}/questions",
        json={"question": "What is the cholesterol level?", "target_language": "en"},
        headers={"X-API-Key": VALID_API_KEY},
    )
    assert resp_insuf.status_code == 200
    assert resp_insuf.json()["status"] == "INSUFFICIENT_EVIDENCE"


def test_translation_endpoint():
    resp = client.post(
        "/api/v1/ai/translate",
        json={
            "text": "Hemoglobin 13.8 g/dL is normal.",
            "source_language": "en",
            "target_language": "hi",
            "preserve_medical_terms": True,
        },
        headers={"X-API-Key": VALID_API_KEY},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["target_language"] == "hi"
    assert "13.8 g/dL" in data["translated_text"]


def test_security_rejections():
    # 1. Unauthenticated -> 401
    resp_unauth = client.post("/api/v1/ai/documents/any_doc/extract")
    assert resp_unauth.status_code == 401

    # 2. Non-existent document -> 404
    resp_404 = client.post(
        "/api/v1/ai/documents/non_existent_doc/extract",
        headers={"X-API-Key": VALID_API_KEY},
    )
    assert resp_404.status_code == 404

    # 3. Unsupported language -> 400
    resp_400 = client.post(
        "/api/v1/ai/translate",
        json={"text": "Hello", "source_language": "en", "target_language": "fr"},
        headers={"X-API-Key": VALID_API_KEY},
    )
    assert resp_400.status_code == 400
    assert "UNSUPPORTED_LANGUAGE" in resp_400.json()["detail"]["error_code"]
