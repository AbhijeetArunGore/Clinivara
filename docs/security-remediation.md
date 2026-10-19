# Clinivara Security Remediation Action Log

**Status**: Completed  
**Release Target**: 1.0.0 Hardened Release  

---

## 1. Remediation Changelog by Phase

### Phase 1: Secrets & Configuration Hardening
- **File**: `clinivara/core/config.py`
  - Added `@model_validator(mode="after")` enforcing production security invariants.
  - Rejects default development keys, test salts, active debug mode, and wildcard CORS when `CLINIVARA_APP_ENV=production`.
  - Added `cors_allowed_origins` typed setting with secure defaults.
- **File**: `.gitignore`
  - Added exclusions for `.env.*`, `!.env.example`, `*.log`, `*.db`, `*.sqlite`, and `.ruff_cache/`.

### Phase 2: API & Storage Hardening
- **File**: `clinivara/api/documents.py`
  - Implemented 1 MB chunked streaming upload reading with immediate enforcement of `max_upload_size_bytes` (25 MB) to prevent denial-of-service memory exhaustion.
- **File**: `clinivara/storage/storage_manager.py`
  - Enforced strict regex validation (`^[a-zA-Z0-9_\-]+$`) on `tenant_id` and `document_id`.
  - Added `_ensure_within_vault()` using `Path.resolve().is_relative_to(vault_root.resolve())` to eliminate CWE-22 path traversal risks.
- **File**: `clinivara/main.py`
  - Added catch-all `Exception` handler returning sanitized JSON error without stack traces or internal filesystem paths.
  - Configured CORS middleware using `settings.cors_allowed_origins`.

### Phase 3: Extraction & Deprecation Remediation
- **Files**:
  - `clinivara/ingestion/validator.py`
  - `clinivara/extraction/pdf_inspector.py`
  - `tests/conftest.py`
  - `tests/test_extraction.py`
  - `tests/test_validator.py`
  - Upgraded PyMuPDF imports to `import pymupdf as fitz` to eliminate deprecation warnings.
  - In `clinivara/core/errors.py`, modernized HTTP 413 constant to `getattr(status, "HTTP_413_CONTENT_TOO_LARGE", 413)`.

### Phase 4: Containerization & Supply Chain
- **File**: `.dockerignore`
  - Created comprehensive Docker build ignore manifest excluding `.git`, `.venv`, `data/`, test caches, and local secrets.
- **File**: `Dockerfile`
  - Added `tesseract-ocr-hin` and `tesseract-ocr-mar` for complete multilingual Indic OCR capability.
  - Replaced ad-hoc pip dependencies with reproducible installation from `pyproject.toml` (`pip install --no-cache-dir .`).
- **File**: `pyproject.toml`
  - Pinned minimum versions for `pandas>=2.2.0`, `numpy>=1.26.0`, `scikit-learn>=1.5.0`, and `scipy>=1.14.0`.

### Phase 5: CI & Continuous Security
- **File**: `.github/workflows/ci.yml`
  - Added GitHub Actions workflow running Ruff lint, Ruff format check, Gitleaks secret scanner, and the full pytest suite on Ubuntu.

### Phase 6: Security Regression Testing
- **File**: `tests/test_security_audit_hardening.py`
  - Added 10 automated test cases verifying fail-closed configuration, path traversal defenses, streaming upload size limits, and security headers.

---

## 2. Operational Deployment Instructions

Before promoting Clinivara to a staging or production healthcare environment:

1. **Inject Production Secrets via Secret Manager**:
   ```bash
   export CLINIVARA_APP_ENV="production"
   export CLINIVARA_DEBUG="false"
   export CLINIVARA_AUTH_SECRET_KEY="$(openssl rand -hex 32)"
   export CLINIVARA_TOKENIZATION_SALT="$(openssl rand -hex 32)"
   export CLINIVARA_CORS_ALLOWED_ORIGINS="https://app.clinivara.internal"
   ```
2. **Reverse Proxy Configuration (Edge Hardening)**:
   Ensure Nginx / Cloudflare has body limits configured:
   ```nginx
   client_max_body_size 25M;
   ```
3. **Database & Storage Vault Mounts**:
   Mount `/app/data/storage` to a dedicated volume with POSIX `0700` permissions.
