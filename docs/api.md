# Clinivara REST API Contract

## Base URL
`/api/v1`

## Authentication
All document endpoints require an API Key supplied via the `X-API-Key` HTTP header.
- Development Default: `X-API-Key: clinivara-dev-client-key-alpha-9921`

---

## 1. Upload & Process Document
`POST /api/v1/documents`

Accepts a multipart file upload (`application/pdf`, `image/png`, or `image/jpeg`). Executes synchronous bounded intake, extraction, de-identification, and validation.

### Request
```http
POST /api/v1/documents HTTP/1.1
Host: localhost:8000
X-API-Key: clinivara-dev-client-key-alpha-9921
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW

------WebKitFormBoundary7MA4YWxkTrZu0gW
Content-Disposition: form-data; name="file"; filename="medical_report.pdf"
Content-Type: application/pdf

<binary content>
------WebKitFormBoundary7MA4YWxkTrZu0gW--
```

### Response (HTTP 201 Created)
```json
{
  "document_id": "a81d4fe6-0310-449e-b7a4-97c27181f9b3",
  "tenant_id": "clinic_default_tenant",
  "status": "APPROVED",
  "sha256_digest": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "received_at": "2026-10-14T04:30:00.000000Z",
  "message": "Document processed with release decision: APPROVED."
}
```

---

## 2. Get Document Processing Status
`GET /api/v1/documents/{document_id}/status`

Retrieves processing stage and permitted quality metadata without disclosing raw clinical text.

### Request
```http
GET /api/v1/documents/a81d4fe6-0310-449e-b7a4-97c27181f9b3/status HTTP/1.1
Host: localhost:8000
X-API-Key: clinivara-dev-client-key-alpha-9921
```

### Response (HTTP 200 OK)
```json
{
  "document_id": "a81d4fe6-0310-449e-b7a4-97c27181f9b3",
  "tenant_id": "clinic_default_tenant",
  "status": "APPROVED",
  "stage": "RELEASE_DECISION_APPROVED",
  "error_code": null,
  "warnings": [],
  "pages_processed": 1,
  "updated_at": "2026-10-14T04:30:01.000000Z"
}
```

---

## 3. Retrieve Approved De-identified Output
`GET /api/v1/documents/{document_id}/result`

Downstream clinical AI interface. Returns strictly policy-approved, independently verified de-identified JSON documents.

### Request
```http
GET /api/v1/documents/a81d4fe6-0310-449e-b7a4-97c27181f9b3/result HTTP/1.1
Host: localhost:8000
X-API-Key: clinivara-dev-client-key-alpha-9921
```

### Response (HTTP 200 OK)
```json
{
  "schema_version": "1.0",
  "document_id": "a81d4fe6-0310-449e-b7a4-97c27181f9b3",
  "tenant_id": "clinic_default_tenant",
  "processing_status": "APPROVED",
  "extraction": {
    "status": "COMPLETED",
    "pages_processed": 1,
    "methods_used": ["embedded_digital_text"],
    "warnings": []
  },
  "deidentification": {
    "status": "COMPLETED",
    "policy_version": "1.0",
    "validation_status": "PASSED",
    "transformed_entity_counts": {
      "NAME": 2,
      "PATIENT_ID": 1,
      "GOV_ID": 1,
      "PHONE": 1,
      "EMAIL": 1
    }
  },
  "clinical_content": {
    "text": "Patient: [NAME]\nDOB: [DATE]\nMRN: [PATIENT_ID]\nDiagnosis: Type 2 Diabetes\nHbA1c: 8.4%\nRx: Metformin 500 mg PO BID",
    "sections": [
      {
        "title": "DIAGNOSIS",
        "content": "Type 2 Diabetes"
      },
      {
        "title": "MEDICATIONS",
        "content": "Metformin 500 mg PO BID"
      }
    ]
  },
  "quality": {
    "schema_valid": true,
    "clinical_content_preserved": true,
    "residual_identifiers_detected": 0
  }
}
```

### Unapproved Output Response (HTTP 409 Conflict)
If a document was rejected or requires manual review:
```json
{
  "error_code": "OUTPUT_NOT_APPROVED",
  "message": "Document a81d4fe6-0310-449e-b7a4-97c27181f9b3 has status 'REJECTED' and is not approved for retrieval.",
  "correlation_id": "corr_9381fba1"
}
```

---

## 4. Secure Deletion
`DELETE /api/v1/documents/{document_id}`

Deletes original files, scratch directories, approved outputs, and metadata.

### Response (HTTP 200 OK)
```json
{
  "document_id": "a81d4fe6-0310-449e-b7a4-97c27181f9b3",
  "deleted": true,
  "status": "DELETED",
  "message": "Document and associated artifacts securely removed according to retention policy."
}
```

---

## 5. Health Status
`GET /api/v1/health`

### Response (HTTP 200 OK)
```json
{
  "status": "UP",
  "service": "clinivara-document-processor",
  "version": "1.0.0",
  "environment": "development",
  "ocr_enabled": true
}
```
