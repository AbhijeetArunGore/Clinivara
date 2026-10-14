# Clinivara Security Specification & Threat Model

## 1. Threat Model & Mitigations

Clinivara treats uploaded medical documents as untrusted binary payloads. The system enforces multi-layered defense-in-depth:

| Threat Vector | Attack Scenario | Defense & Mitigation |
| :--- | :--- | :--- |
| **MIME / File Signature Spoofing** | Attacker uploads an executable or script disguised with `.pdf` extension. | Clinivara inspects true file magic bytes independently (`%PDF-`, `\x89PNG`, `\xff\xd8\xff`). Client `Content-Type` is never trusted. |
| **Path Traversal Attacks** | Malicious filename such as `../../etc/passwd` or `..\Windows\cmd.exe`. | Filenames are stripped of directory components and sanitized via regex. Server-generated UUID4 identifiers are used for filesystem storage. |
| **Decompression Bombs (Zip/Pixel Bombs)** | Tiny PNG/JPEG with extreme dimensions (e.g. 50,000x50,000 px) causing memory exhaustion. | Pillow safe inspection verifies dimensions without loading full raster buffers. Limits enforced: max dimension 8,000px, max 50 MP. |
| **Resource Exhaustion / Large Files** | Uploading multi-gigabyte files or 10,000-page PDFs. | Max file size capped at 25 MB (`CLINIVARA_MAX_UPLOAD_SIZE_BYTES`). Max PDF pages capped at 50 (`CLINIVARA_MAX_PDF_PAGES`). Streaming chunk checks. |
| **Encrypted / Password-Protected PDFs** | Encrypted PDFs bypassing internal scanners. | PyMuPDF verifies `doc.is_encrypted`. Encrypted documents are immediately rejected by policy. |
| **Cross-Tenant Access / IDOR** | Tenant A attempts to access Tenant B's documents by guessing document IDs. | Document IDs are cryptographically random UUID4. Every document access requires tenant verification (`meta["tenant_id"] == caller_tenant`). |
| **Log Injection / Log Tampering** | Patient names or inputs contain `\r\n` to forge audit events. | Audit logger sanitizes all input strings by stripping CR, LF, and control codes (`re.sub(r"[\r\n\x00-\x1f\x7f-\x9f]", " ", text)`). |
| **Clinical Text / Identifier Leakage** | Patient names, phone numbers, or raw OCR text leaked in logs or error messages. | Explicit blacklist in audit logger redacting sensitive fields. Generic client error responses with correlation IDs. |
| **Dictionary Attacks on Pseudonyms** | Unsalted hashing of phone numbers or MRNs allowing precomputed rainbow table reversal. | Pseudonyms use HMAC-SHA256 with high-entropy secret salt (`CLINIVARA_TOKENIZATION_SALT`). Original values never stored with tokens in public outputs. |

---

## 2. Authentication & Authorization

1. **Header-Based Authentication**:
   - Clients supply their API key via the `X-API-Key` HTTP header.
2. **Constant-Time Verification**:
   - Keys are validated using `secrets.compare_digest` to prevent timing attacks.
3. **Tenant Mapping**:
   - Each API key maps deterministically to a tenant identifier.
4. **Data Isolation**:
   - Boundary A, Boundary B, Boundary C, and Token Vault partition storage by `tenant_id`.

---

## 3. Defensive HTTP Headers

All HTTP responses automatically include security headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Content-Security-Policy: default-src 'none'; frame-ancestors 'none';`

---

## 4. Audit & Observability

Audit events are appended to a secure JSON Lines log (`data/audit/audit_events.jsonl`). Permitted fields:
- `event_id`: Unique event identifier
- `timestamp`: UTC ISO-8601
- `tenant_id`: Authenticated tenant
- `document_id`: Random document ID
- `correlation_id`: Request correlation ID
- `event_type`: Categorized lifecycle event (`DOCUMENT_UPLOADED`, `RELEASE_APPROVED`, etc.)
- `status`: `SUCCESS`, `FAILURE`, or `WARNING`
- `details`: Non-sensitive operational metadata (page count, execution method, duration, warning count).
