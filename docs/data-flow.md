# Clinivara Data Flow & Artifact Lifecycle

```mermaid
graph TD
    Client[Client / Ingestion API] -->|POST /api/v1/documents| Ingestion[1. Ingestion Validator]
    Ingestion -->|Magic bytes, Size, Decomp bomb OK| Stager[2. Document Stager]
    Stager -->|Saves raw document| BoundaryA[(Boundary A: Raw Vault)]
    Stager -->|Invokes extraction| Extractor[3. Document Extractor]

    Extractor -->|Selective Page Render| BoundaryB[(Boundary B: Scratch)]
    BoundaryB -->|Runs OCR| Tesseract[Tesseract OCR Engine]
    Tesseract -->|Extracts Text & Quality Metrics| Extractor
    Extractor -.->|Deletes temp image| BoundaryB

    Extractor -->|Raw Aggregated Text| Cleaner[4. Text Cleaner & Normalizer]
    Cleaner -->|Unicode, Whitespace, Preserves Units| DeidEngine[5. De-identification Engine]

    DeidEngine -->|Presidio + Custom Recognizers| DeidEngine
    DeidEngine -->|Transforms Entities| ReleaseGate[6. Independent Release Gate]

    ReleaseGate -->|Pass 2 Residual Scan & Preservation Check| Evaluator{Pass?}
    Evaluator -->|Residuals Detected| RejectState[Status: REJECTED]
    Evaluator -->|Uncertain / Flagged| ReviewState[Status: REVIEW_REQUIRED]
    Evaluator -->|0 Residuals & Preserved| BoundaryC[(Boundary C: Approved Vault)]

    BoundaryC -->|GET /api/v1/documents/{id}/result| Downstream[Downstream Clinical AI]
```

## Step-by-Step Lifecycle

1. **Intake & Verification**:
   - Client sends multipart file with `X-API-Key`.
   - File signature is validated (magic bytes).
   - Filename is sanitized to prevent directory traversal; a random UUID4 is assigned.
   - Raw bytes are committed to `Boundary A: Raw Vault`.

2. **Extraction & Selective OCR**:
   - PyMuPDF opens PDF defensively.
   - High-density text pages are extracted digitally.
   - Low-density text pages are rendered to 300 DPI in `Boundary B: Scratch` and processed via Tesseract OCR.
   - Rendered images are deleted immediately from scratch storage upon completion.

3. **Normalization**:
   - Unicode NFKC normalization separates ligatures while keeping micro/Greek symbols.
   - Line endings are unified; form feeds and replacement characters are cleaned.
   - Clinical units, negative signs, and comparison operators are protected.

4. **De-identification**:
   - Presidio Analyzer + custom recognizers detect names, MRNs, Aadhaar, PAN, ABHA, phones, dates.
   - Protected medical terms are whitelisted.
   - Irreversible redaction masks (e.g. `[NAME]`, `[PATIENT_ID]`) are substituted.

5. **Independent Second-Pass Release Gate**:
   - Secondary scanner checks sanitized text for residual patterns or leakage.
   - Clinical preservation checker validates retention of laboratory numbers and vital signs.
   - If clean: committed to `Boundary C: Approved Vault` with status `APPROVED`.
   - If residual detected: status becomes `REJECTED`.

6. **Downstream Retrieval & Deletion**:
   - Consumers call `/api/v1/documents/{id}/result` to fetch approved structured JSON.
   - Unapproved documents return HTTP 409 Conflict.
   - Upon deletion (`DELETE`), all files in Boundary A, Boundary C, and metadata are erased.
