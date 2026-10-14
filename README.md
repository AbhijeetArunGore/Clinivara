# Clinivara: Privacy-First Clinical Document Processing Backend

Clinivara is a security-first, HIPAA- and DPDP-aligned clinical document intake, extraction, and de-identification engine designed to protect patient privacy before any data reaches downstream clinical AI models, vector stores, or LLM agents.

---

## The Processing Invariant

```
Original Report -> Secure Intake -> Extraction -> Normalization -> Sensitive Entity Detection -> De-identification -> Independent Validation -> Approved Output
```

No downstream consumer may receive unvalidated extracted text or raw reports. Documents failing security checks, extraction quality, or independent privacy verification are quarantined or rejected (`REJECTED` or `REVIEW_REQUIRED`). Unsafe output is never silently released.

---

## Key Capabilities

- **Secure Document Upload**: Magic-byte signature verification (`%PDF-`, `PNG`, `JPEG`), path traversal rejection, image decompression bomb protection, file size and page count bounding.
- **Defensive Extraction & Selective OCR**: High-performance digital extraction via PyMuPDF with selective Tesseract OCR fallback on low-text or scanned pages. Ephemeral scratch images are automatically shredded.
- **Conservative Clinical Normalization**: Unicode NFKC cleaning, line-ending standardization, and clinical section parsing. Preserves negative signs, laboratory units (`mg/dL`, `mmol/L`, `mmHg`), and medication dosages (`500 mg PO BID`).
- **Clinical & Regional Entity Detection**: Presidio Analyzer, spaCy NLP, and custom recognizers for Hospital MRNs, Indian Aadhaar numbers, PAN cards, ABHA IDs, phone numbers, and doctor names.
- **Medical Whitelist Protection**: Preserves clinical diagnoses and standard medications from erroneous redaction.
- **Independent Privacy Release Gate**: Second-pass residual scanner and clinical preservation verifier ensuring fail-closed protection.
- **Multi-Tenant Data Isolation**: Storage partitioned into Boundary A (Raw Vault), Boundary B (Scratch), Boundary C (Approved Output), and Token Vault.
- **Privacy-Preserving Audit Logging**: Immutable JSON Lines audit events with log injection sanitization.

---

## Quickstart

### 1. Requirements
- Python 3.12+
- Tesseract OCR (`tesseract` on system PATH)

### 2. Local Setup
```bash
# Create virtual environment
uv venv .venv --python 3.12

# Install dependencies
uv pip install --python .venv -r requirements.txt
# or
uv pip install --python .venv .

# Download spaCy model
.venv\Scripts\python -m spacy download en_core_web_sm
```

### 3. Run Automated Tests
```bash
.venv\Scripts\pytest -v
```

### 4. Run Privacy & Clinical Preservation Benchmark
```bash
.venv\Scripts\python evaluation/evaluate_privacy.py
```

### 5. Run the REST API Server
```bash
.venv\Scripts\uvicorn clinivara.main:app --reload --host 127.0.0.1 --port 8000
```

---

## API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/documents` | Secure upload, extraction, de-identification, and validation. |
| `GET` | `/api/v1/documents/{id}/status` | Safe processing status and quality metadata. |
| `GET` | `/api/v1/documents/{id}/result` | Retrieve approved de-identified output (blocks unapproved). |
| `DELETE` | `/api/v1/documents/{id}` | Secure deletion of raw files, approved output, and metadata. |
| `GET` | `/api/v1/health` | Container readiness and operational monitoring. |

---

## Documentation
- [Architecture & Trust Boundaries](docs/architecture.md)
- [Security & Threat Model](docs/security.md)
- [De-identification Policy](docs/deidentification-policy.md)
- [Data Flow & Lifecycle](docs/data-flow.md)
- [API Contract Specification](docs/api.md)
- [Testing Strategy & Results](docs/testing.md)
- [Deployment Guide](docs/deployment.md)

---

## Limitations & Production Risks
- Tesseract OCR accuracy is dependent on source scan quality and DPI.
- Second-pass verification detects known residual patterns, but cannot mathematically guarantee zero re-identification risk in high-dimensional patient datasets.
- For public cloud production, persistent storage must be backed by encrypted block or object stores with strict KMS key rotation policies.
