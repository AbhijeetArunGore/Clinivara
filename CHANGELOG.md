# Changelog - Clinivara Engineering Milestone 1

All notable changes and architectural deliverables implemented in Milestone 1.

## [1.0.0] - 2026-10-14

### Initial Release: Privacy-First Clinical Document Processing Backend

#### Ingestion & Security
- Implemented `detect_file_signature` validating magic bytes (`%PDF-`, `PNG`, `JPEG`) independently from client-supplied `Content-Type`.
- Implemented `inspect_image_safety` using Pillow to protect against decompression and pixel bombs.
- Implemented defensive PDF preliminary checks rejecting encrypted or oversized documents (> 50 pages).
- Implemented filename sanitization against path traversal attacks (`../../`) and null bytes.
- Implemented SHA-256 bounded chunk digest calculation.
- Implemented constant-time API key verification (`secrets.compare_digest`) and multi-tenant isolation.
- Implemented HTTP security middleware: HSTS, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, CSP.

#### Text Extraction & Selective OCR
- Implemented `PDFInspector` using PyMuPDF for embedded digital text extraction and metadata sanitization.
- Implemented selective Tesseract OCR fallback for low-text density pages (< 50 chars).
- Implemented high-resolution (300 DPI) rendering for OCR fallback.
- Implemented true OCR confidence extraction across word-level tokens without score fabrication.
- Implemented ephemeral Boundary B scratch directory cleanup ensuring intermediate images are wiped immediately.

#### Clinical Normalization & Data Quality
- Implemented `TextCleaner` with Unicode NFKC normalization and line-ending standardization.
- Implemented `DataQualityValidator` ensuring clinical operators (`<`, `>`, `≤`, `≥`, `±`, `-`) and laboratory units (`mg/dL`, `mmol/L`, `mmHg`, `%`) are preserved.
- Implemented clinical section parsing (`CHIEF COMPLAINT`, `HISTORY`, `MEDICATIONS`, `LABORATORY`, `PLAN`).

#### De-identification & Clinical Whitelisting
- Implemented `DeidentificationEngine` combining Microsoft Presidio Analyzer, spaCy NLP, and custom recognizers.
- Registered custom recognizers for Hospital MRNs, Indian Aadhaar numbers, PAN cards, ABHA IDs, phone numbers, and doctor names.
- Implemented clinical term whitelisting to protect medical diagnoses, lab tests, and medications from improper redaction.
- Implemented `TokenVault` for cryptographically salted HMAC pseudonymization.

#### Independent Validation & Release Gate
- Implemented `ResidualIdentifierScanner` as an independent second-pass verification layer.
- Implemented `ClinicalPreservationChecker` to ensure critical medical findings are not stripped.
- Implemented `ReleaseGate` enforcing fail-closed release: only documents with 0 residual identifiers and verified preservation transition to `APPROVED`.
- Enforced strict Pydantic model validation on `ApprovedDocumentOutput`.

#### Storage & Audit
- Partitioned storage into Boundary A (Raw Vault), Boundary B (Scratch), Boundary C (Approved Output), and Token Vault.
- Implemented append-only structured JSON Lines audit logger with log injection defense.
- Implemented secure deletion purging artifacts across all boundaries.

#### Evaluation & Testing
- Developed comprehensive automated test suite across unit, adversarial security, and end-to-end integration tests.
- Developed repeatable benchmark script (`evaluate_privacy.py`) measuring Precision, Recall, F1, and preservation rates.
