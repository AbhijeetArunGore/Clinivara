# Clinivara Architectural Specification

## 1. System Mission & Core Invariant

Clinivara is a security-first clinical document processing backend engineered to ingest sensitive medical records, extract high-fidelity text (via digital PDF extraction or selective Tesseract OCR fallback), normalize clinical data, de-identify direct and indirect patient identifiers, and subject the output to an independent privacy release gate.

The pipeline enforces this strict invariant:
```
Original Report -> Secure Intake -> Extraction -> Normalization -> Sensitive Entity Detection -> De-identification -> Independent Validation -> Approved Output
```
**Downstream invariant**: No downstream clinical AI consumer, LLM agent, or vector database may ever receive unvalidated extracted text or original reports.

---

## 2. Logical Components

Clinivara is structured into decoupled modules with explicit boundaries:

```
clinivara/
├── api/             # FastAPI REST routes (upload, status, result, delete, health) & auth dependencies
├── core/            # Configuration (Pydantic Settings), sanitized error hierarchy, security primitives
├── ingestion/       # Upload validation (magic bytes, MIME check, size/page/bomb limits) & Boundary A staging
├── extraction/      # Digital PDF extraction (PyMuPDF), selective Tesseract OCR fallback, page provenance
├── normalization/   # Unicode (NFKC) normalization, whitespace cleaning, clinical symbol/unit preservation
├── deidentification/# Presidio Analyzer/Anonymizer, spaCy NLP, custom clinical & regional recognizers, token vault
├── validation/      # Independent 2nd-pass residual scanner, clinical preservation checker, fail-closed release gate
├── storage/         # Segregated vault filesystem manager (Boundary A, Boundary B scratch, Boundary C, Token Vault)
├── audit/           # Append-only structured JSON Lines audit logger with log injection defense
├── schemas/         # Strongly-typed Pydantic request/response/event contracts
└── main.py          # Application entrypoint, security headers, CORS, exception handling
```

---

## 3. Trust Boundaries

Clinivara enforces four isolated data boundaries:

| Boundary | Purpose | Access Restrictions | Ephemeral / Persistent |
| :--- | :--- | :--- | :--- |
| **Boundary A: Raw Documents** (`boundary_a_raw/`) | Original uploaded PDFs and raster images. Stored under server-generated UUID4 (never original client filename). | Restricted to Ingestion & Extraction services. Never exposed via public web roots or downstream APIs. | Retained per organization data retention policy. |
| **Boundary B: Scratch Artifacts** (`boundary_b_scratch/`) | Temporary rendered page images (300 DPI) for selective OCR and intermediate OCR text. | Restricted exclusively to OCR workers. | **Strictly ephemeral**: Auto-deleted immediately after page processing or on failure. |
| **Boundary C: Approved Vault** (`boundary_c_approved/`) | Fully validated, policy-approved de-identified JSON documents and structured sections. | Accessible only to authorized downstream consumers via `/api/v1/documents/{id}/result`. | Persistent approved records. |
| **Token Vault** (`token_vault/`) | Isolated HMAC-SHA256 mappings between raw identifiers and pseudonyms if longitudinal patient linkage is enabled. | Strictly separated from Boundary C. Never included in API responses or public logs. | Protected key-vault access only. |

---

## 4. Extraction & Selective OCR Orchestration

Rather than executing slow, noisy OCR indiscriminately on every document page:
1. **Digital PDF Inspection**: PyMuPDF inspects each page for embedded digital text.
2. **Text Density Threshold**: If a page contains $\ge 50$ characters, digital text is extracted directly.
3. **Selective Fallback**: If a page contains $< 50$ characters (e.g. scanned letterhead, faxed report, embedded image), that specific page is rendered to 300 DPI in Boundary B scratch storage and processed through Tesseract OCR.
4. **Immediate Cleanup**: Temporary raster renders are deleted immediately after OCR completes.
5. **Quality Signals**: Token counts and confidence metrics are captured without logging raw text.

---

## 5. Independent Second-Pass Privacy Gate

Detection components (Presidio, spaCy, regex) are probabilistic detection mechanisms, not mathematical proof of anonymity. Clinivara therefore implements an independent, non-collaborative second-pass verification stage:
- Scans for residual unredacted identifiers (names, MRNs, Aadhaar, PAN, phones, emails).
- Checks for internal path or token leakage.
- Verifies clinical utility preservation (diagnoses, laboratory values, vital signs).
- Enforces fail-closed release:
  - **APPROVED**: Zero residual identifiers detected, clinical facts preserved, schema valid.
  - **REJECTED**: Residual identifier detected; output blocked from downstream retrieval.
  - **REVIEW_REQUIRED**: Uncertain confidence or borderline pattern flagged for human review.
