"""
Adversarial security tests: path traversal, cross-tenant isolation, log injection,
unauthorized retrieval, and spoofed payloads.
"""

import io
import pytest
from fastapi.testclient import TestClient

from clinivara.audit.audit_logger import sanitize_log_string
from clinivara.core.errors import SecurityViolationError
from clinivara.core.security import sanitize_filename


def test_path_traversal_filename_sanitization():
    # Dangerous path traversal payloads
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\Windows\\System32\\cmd.exe") == "cmd.exe"
    assert sanitize_filename("normal_file.pdf") == "normal_file.pdf"

    # Null byte rejection
    with pytest.raises(SecurityViolationError):
        sanitize_filename("report.pdf\x00.exe")


def test_log_injection_sanitization():
    malicious_input = "Document processed successfully.\r\nADMIN_OVERRIDE: Granted\n"
    sanitized = sanitize_log_string(malicious_input)
    assert "\r" not in sanitized
    assert "\n" not in sanitized
    assert "ADMIN_OVERRIDE" in sanitized


def test_unauthenticated_request_rejection(client):
    response = client.get("/api/v1/documents/some-uuid/status")
    assert response.status_code == 401


def test_cross_tenant_isolation(client, auth_headers, tenant_two_headers, synthetic_pdf_bytes):
    # Tenant 1 uploads document
    files = {"file": ("report.pdf", synthetic_pdf_bytes, "application/pdf")}
    upload_res = client.post("/api/v1/documents", headers=auth_headers, files=files)
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["document_id"]

    # Tenant 2 attempts to fetch status of Tenant 1's document
    status_res = client.get(f"/api/v1/documents/{doc_id}/status", headers=tenant_two_headers)
    # Tenant 2 is isolated and cannot see Tenant 1's document (returns 404 or 403)
    assert status_res.status_code in (403, 404)

    # Tenant 2 attempts to fetch result of Tenant 1's document
    result_res = client.get(f"/api/v1/documents/{doc_id}/result", headers=tenant_two_headers)
    assert result_res.status_code in (403, 404)

    # Cleanup with Tenant 1
    client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers)


def test_security_headers_present(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert "Strict-Transport-Security" in res.headers
    assert "Content-Security-Policy" in res.headers
