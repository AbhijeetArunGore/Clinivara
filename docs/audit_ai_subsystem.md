# Phase Zero Audit: Clinivara AI & Data Science Subsystem

**Document Version**: 1.0.0  
**Date**: 2026-10-16  
**Auditor**: Senior Healthcare AI Architect & Applied NLP/MLOps Team

---

## 1. Executive Summary

Clinivara's Milestone 1 established a security-first ingestion and privacy boundary:
$$\text{Original Report} \longrightarrow \text{Secure Intake} \longrightarrow \text{Extraction} \longrightarrow \text{Normalization} \longrightarrow \text{Detection} \longrightarrow \text{De-identification} \longrightarrow \text{Validation} \longrightarrow \text{Approved Output}$$

All 23 baseline unit, adversarial security, and end-to-end integration tests are passing with a 100% success rate. The objective of Milestone 2 is to construct the **Data Science, AI, NLP, LLM, Multilingual, and Clinical RAG Subsystem** on top of this verified foundation.

---

## 2. Existing Components to Reuse

The existing pipeline is mature and must remain the authoritative security boundary:

1. **Ingestion & Validation** (`clinivara/ingestion/`):
   - `detect_file_signature`: Magic byte inspection (`%PDF-`, `\x89PNG`, `\xff\xd8\xff`).
   - `inspect_image_safety`: Decompression and pixel-bomb protection via Pillow.
   - `document_stager`: Defensive staging into Boundary A with UUID4 identifiers.
2. **Extraction & Selective OCR** (`clinivara/extraction/`):
   - `PDFInspector`: Defensive PyMuPDF digital text extraction.
   - `OCREngine`: Tesseract OCR fallback with confidence reporting.
3. **Normalization & Quality** (`clinivara/normalization/`):
   - `TextCleaner`: Unicode NFKC normalization and line-ending standardization.
   - `DataQualityValidator`: Clinical operator and unit preservation verification.
4. **De-identification & Vaults** (`clinivara/deidentification/`):
   - Custom pattern recognizers for Indian identifiers (Aadhaar, PAN, ABHA, MRN, Phone).
   - Clinical whitelist protecting diagnostic and medication terminology.
   - `TokenVault`: Isolated HMAC-SHA256 pseudonym storage.
5. **Storage & Isolation Boundaries** (`clinivara/storage/`):
   - Boundary A (Raw Vault), Boundary B (Scratch), Boundary C (Approved Output), Token Vault.
   - Secure deletion purging records across all boundaries.
6. **Release Gate** (`clinivara/validation/`):
   - `ResidualIdentifierScanner`: Independent second-pass detection.
   - `ReleaseGate`: Strict fail-closed release invariant (`APPROVED` vs `REJECTED`).
7. **Security & Audit** (`clinivara/core/security.py` & `clinivara/audit/`):
   - Constant-time API key verification, tenant isolation, and sanitized JSONL audit logger.

---

## 3. Existing Components Requiring Extension

1. **Configuration** (`clinivara/core/config.py`):
   - Add AI settings: active LLM provider (`mock`, `openai`, `local`), model names, temperature, default target language (`en`, `hi`, `mr`), embedding model, RAG top-k, and citation thresholds.
2. **Extraction OCR Engine** (`clinivara/extraction/ocr_engine.py`):
   - Add installed OCR language detection diagnostics (verifying presence of `eng`, `hin`, `mar` packs).
3. **API Router** (`clinivara/api/router.py`):
   - Mount new `/api/v1/ai` endpoints alongside existing document routes.

---

## 4. Missing AI & Data Science Capabilities (Target Scope)

The following modular subsystems must be built:

| Module | Description |
| :--- | :--- |
| **Multilingual Subsystem** (`clinivara/multilingual/`) | Pluggable language registry (`en`, `hi`, `mr`), language detection, Devanagari Unicode normalization, translation and transliteration adapters, and multilingual clinical terminology dictionaries. |
| **Clinical NLP Subsystem** (`clinivara/nlp/`) | Multilingual clinical tokenizer, section detection (English/Hindi/Marathi), and negation/uncertainty detection. |
| **Clinical Fact Extraction** (`clinivara/clinical/`) | Document classifier (12 categories), Pydantic v2 clinical observation schemas, lab table parser, unit validator with UCUM mapping, and baseline LOINC dictionary. |
| **LLM Orchestration Layer** (`clinivara/ai/`) | Provider-neutral interface (`LLMProvider`) with `MockLLMProvider`, `OpenAICompatibleProvider`, versioned prompt registry (Prompts A–G), and safety guardrails. |
| **Clinical RAG Subsystem** (`clinivara/rag/`) | Section/table-aware chunker, multilingual embedding provider, document-isolated vector index, citation mapper, and evidence sufficiency verifier. |
| **Evaluation Framework** (`clinivara/evaluation/`) | Comprehensive benchmarks for extraction precision/recall/F1, RAG retrieval accuracy, generation faithfulness, and multilingual preservation. |
| **AI REST API** (`clinivara/api/ai.py`) | Stable, versioned `/api/v1/ai` endpoints for health, capabilities, extraction, grounded explanation, document Q&A, and translation. |

---

## 5. Security & Privacy Boundaries for the AI Subsystem

1. **Strict Input Boundary**: AI components consume **ONLY** `ApprovedDocumentOutput` from Boundary C. They never access raw PDFs/images in Boundary A or pseudonym mappings in the Token Vault.
2. **Deterministic Offline Execution**: In tests and default local mode, all AI operations run through deterministic mock/rule providers without paid or external network APIs.
3. **Audit Protection**: LLM prompts and raw clinical outputs are never logged in plain text. Only operational metadata (duration, token count, validation status) is written to audit logs.
4. **Tenant Isolation**: RAG indexes and clinical extractions are strictly isolated by `tenant_id` and `document_id`.

---

## 6. Phased Implementation Roadmap

1. **Stage 1**: Shared schemas, AI configuration, and error hierarchy.
2. **Stage 2**: Multilingual pipeline (language registry, detection, Devanagari normalization, terminology).
3. **Stage 3**: Clinical NLP & fact extraction (document classification, sectioning, lab tables, units, negation).
4. **Stage 4**: LLM provider layer & versioned prompt registry (Prompts A–G, mock provider, structured output).
5. **Stage 5**: Clinical RAG & grounded question answering (chunking, embeddings, retrieval, citations).
6. **Stage 6**: Validation, evidence consistency checking, and safety guardrails.
7. **Stage 7**: AI API endpoints (`/api/v1/ai/...`) and route integration.
8. **Stage 8**: Automated tests (unit, multilingual, adversarial, e2e) and evaluation benchmarks.
9. **Stage 9**: Documentation, OpenAPI examples, and handover deliverables.
