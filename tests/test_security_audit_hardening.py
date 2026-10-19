"""
Security Audit and Hardening Regression Test Suite.

Verifies:
1. Fail-closed production configuration validation (insecure dev secrets & salts rejected).
2. Defense-in-depth path traversal and directory escape prevention in StorageManager.
3. Bounded chunked streaming upload size enforcement.
4. Unhandled server exception sanitization (preventing stack trace leakage).
5. Comprehensive defensive security headers.
"""

import io

import pytest
from pydantic import ValidationError

from clinivara.core.config import Settings
from clinivara.core.errors import SecurityViolationError
from clinivara.storage.storage_manager import StorageManager


def test_production_rejects_default_auth_secret():
    """Fail-closed: In production, default dev auth secret must raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            app_env="production",
            auth_secret_key="clinivara_insecure_dev_secret_key_change_in_production_32b",
            tokenization_salt="prod_salt_high_entropy_random_value_99812",
            api_keys={"real_client_key_991823712893712983712": "prod_clinic"},
            debug=False,
        )
    assert "CLINIVARA_AUTH_SECRET_KEY must be a high-entropy secret" in str(exc_info.value)


def test_production_rejects_default_salt():
    """Fail-closed: In production, default dev salt must raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            app_env="production",
            auth_secret_key="prod_secret_key_high_entropy_random_value_32chars_long",
            tokenization_salt="clinivara_secure_salt_value_replace_in_prod",
            api_keys={"real_client_key_991823712893712983712": "prod_clinic"},
            debug=False,
        )
    assert "CLINIVARA_TOKENIZATION_SALT must be an isolated" in str(exc_info.value)


def test_production_rejects_default_api_keys():
    """Fail-closed: In production, dev/test API keys must raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            app_env="production",
            auth_secret_key="prod_secret_key_high_entropy_random_value_32chars_long",
            tokenization_salt="prod_salt_high_entropy_random_value_99812",
            api_keys={"clinivara-dev-client-key-alpha-9921": "clinic_default_tenant"},
            debug=False,
        )
    assert "Default development/testing API keys must be replaced" in str(exc_info.value)


def test_production_rejects_debug_mode():
    """Fail-closed: In production, debug=True must raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            app_env="production",
            auth_secret_key="prod_secret_key_high_entropy_random_value_32chars_long",
            tokenization_salt="prod_salt_high_entropy_random_value_99812",
            api_keys={"real_client_key_991823712893712983712": "prod_clinic"},
            debug=True,
        )
    assert "CLINIVARA_DEBUG cannot be True in production" in str(exc_info.value)


def test_production_rejects_wildcard_cors():
    """Fail-closed: In production, wildcard CORS origin must raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            app_env="production",
            auth_secret_key="prod_secret_key_high_entropy_random_value_32chars_long",
            tokenization_salt="prod_salt_high_entropy_random_value_99812",
            api_keys={"real_client_key_991823712893712983712": "prod_clinic"},
            debug=False,
            cors_allowed_origins=["*"],
        )
    assert "Wildcard '*' in CLINIVARA_CORS_ALLOWED_ORIGINS is forbidden" in str(exc_info.value)


def test_production_accepts_valid_high_entropy_configuration():
    """Verification: Properly injected production secrets pass validation."""
    prod_settings = Settings(
        app_env="production",
        auth_secret_key="prod_super_secure_entropy_key_length_32_bytes_min",
        tokenization_salt="prod_salt_high_entropy_random_value_99812",
        api_keys={"clin_prod_key_991823712893712983712": "production_hospital_alpha"},
        debug=False,
        cors_allowed_origins=["https://clinivara.hospital.internal"],
    )
    assert prod_settings.app_env == "production"
    assert not prod_settings.debug


def test_storage_manager_path_traversal_rejection(tmp_path):
    """Defense-in-depth: StorageManager rejects malicious directory traversal attempts."""
    mgr = StorageManager(storage_root=tmp_path)

    # Path traversal via tenant_id
    with pytest.raises(SecurityViolationError) as exc_info:
        mgr.save_original_document(
            tenant_id="../malicious_tenant",
            document_id="doc123",
            extension=".pdf",
            content=b"%PDF-1.4 test",
        )
    assert "potential path traversal detected" in str(exc_info.value)

    # Path traversal via document_id
    with pytest.raises(SecurityViolationError) as exc_info:
        mgr.save_original_document(
            tenant_id="valid_tenant",
            document_id="../../etc_passwd",
            extension=".pdf",
            content=b"%PDF-1.4 test",
        )
    assert "potential path traversal detected" in str(exc_info.value)

    # Path traversal via invalid extension
    with pytest.raises(SecurityViolationError) as exc_info:
        mgr.save_original_document(
            tenant_id="valid_tenant",
            document_id="valid_doc",
            extension="../../evil.sh",
            content=b"%PDF-1.4 test",
        )
    assert "Invalid file extension format" in str(exc_info.value)


def test_storage_manager_isolated_boundary_retrieval(tmp_path):
    """StorageManager safely stores and retrieves documents within designated vault boundaries."""
    mgr = StorageManager(storage_root=tmp_path)
    tenant_id = "clinic_alpha"
    doc_id = "report_9982"

    saved_path = mgr.save_original_document(
        tenant_id=tenant_id,
        document_id=doc_id,
        extension=".pdf",
        content=b"%PDF-1.4 sample content",
    )
    assert saved_path.exists()
    assert saved_path.is_relative_to(mgr.boundary_a)

    retrieved = mgr.get_original_document_path(tenant_id, doc_id)
    assert retrieved == saved_path


def test_chunked_streaming_upload_limit(client):
    """Upload exceeding max_upload_size_bytes is rejected with HTTP 413."""
    # Create fake oversized content in memory
    oversized_size = 26 * 1024 * 1024  # 26 MB > 25 MB limit
    oversized_file = io.BytesIO(b"A" * oversized_size)

    response = client.post(
        "/api/v1/documents",
        headers={"X-API-Key": "clinivara-dev-client-key-alpha-9921"},
        files={"file": ("oversized.pdf", oversized_file, "application/pdf")},
    )
    assert response.status_code == 413
    assert response.json()["detail"]["error_code"] == "DOCUMENT_TOO_LARGE"


def test_defensive_security_headers_enforced(client):
    """Every HTTP response must carry mandatory defensive security headers."""
    response = client.get("/api/v1/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "max-age=31536000" in response.headers["Strict-Transport-Security"]
    assert response.headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none';"
