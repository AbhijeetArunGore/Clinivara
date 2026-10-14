# Clinivara Testing & Evaluation Strategy

## 1. Automated Test Architecture

Clinivara includes comprehensive tests covering every phase of the pipeline:

| Test File | Type | What is Verified |
| :--- | :--- | :--- |
| `tests/test_validator.py` | Unit | File magic bytes (%PDF, PNG, JPEG), empty files, spoofed extensions, decompression bombs, encrypted PDF rejection. |
| `tests/test_extraction.py` | Unit | Digital PDF text extraction, selective OCR fallback on low-text pages, direct raster image OCR, scratch directory cleanup. |
| `tests/test_normalization.py` | Unit | Unicode NFKC normalization, whitespace handling, preservation of lab symbols, signs, dosages, and clinical section parsing. |
| `tests/test_deidentification.py` | Unit | Entity detection (Names, MRN, Aadhaar, PAN, ABHA, Phone, Email, Dates), Presidio transformations, clinical whitelist protection. |
| `tests/test_release_gate.py` | Unit | Second-pass residual scanner, clinical preservation checker, fail-closed rejection on residual leaks, Pydantic invariant enforcement. |
| `tests/test_security_adversarial.py` | Adversarial | Path traversal filenames (`../../etc/passwd`), null bytes, log injection, unauthenticated access, cross-tenant isolation, security headers. |
| `tests/test_e2e_pipeline.py` | Integration | Full end-to-end pipeline: digital PDF & scanned image intake -> extraction -> de-id -> release gate -> result retrieval -> secure deletion. |

---

## 2. Test Execution Commands

Run the full automated test suite:
```bash
pytest -v
```

Run only security and adversarial tests:
```bash
pytest -v tests/test_security_adversarial.py
```

Run with coverage report:
```bash
pytest --cov=clinivara --cov-report=term-missing
```

---

## 3. Evaluation & Privacy Metrics

The repeatable benchmark script evaluates detection precision, recall, residual leak rate, and clinical fact preservation against annotated synthetic medical records:

```bash
python evaluation/evaluate_privacy.py
```

Key Metrics Measured:
- **Precision**: Proportion of redacted entities that were true sensitive identifiers (preventing over-scrubbing).
- **Recall**: Proportion of true sensitive identifiers that were successfully detected and transformed.
- **F1 Score**: Harmonic mean of Precision and Recall.
- **Residual Leaks**: Identifier count detected after the independent release gate.
- **Clinical Preservation Rate**: Percentage of ground-truth medical facts (diagnoses, lab values, dosages) preserved intact.
- **Average Processing Latency**: Wall-clock milliseconds per document.
