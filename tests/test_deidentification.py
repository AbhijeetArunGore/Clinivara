"""
Unit tests for sensitive entity detection, clinical whitelisting, and de-identification.
"""

from clinivara.deidentification.engine import deidentification_engine


def test_entity_detection_and_redaction():
    text = (
        "Patient: Robert Smith\n"
        "Attending: Dr. Priya Nair\n"
        "MRN: MRN-991283\n"
        "Aadhaar: 3412 8765 4321\n"
        "PAN: ABCDE1234F\n"
        "ABHA: 91-1234-5678-9012\n"
        "Phone: +91-9876543210\n"
        "Email: robert.smith@med.example.com\n"
        "Date of Exam: 15/08/2023\n"
        "Diagnosis: Type 2 Diabetes\n"
        "Lab: HbA1c 8.2%\n"
        "Rx: Metformin 500 mg"
    )

    sanitized, counts, summary = deidentification_engine.deidentify(
        text=text,
        tenant_id="tenant_test",
        document_id="doc_test_1",
        correlation_id="corr_test_1",
    )

    # Identifiers must be removed
    assert "Robert Smith" not in sanitized
    assert "Dr. Priya Nair" not in sanitized
    assert "MRN-991283" not in sanitized
    assert "3412 8765 4321" not in sanitized
    assert "ABCDE1234F" not in sanitized
    assert "91-1234-5678-9012" not in sanitized
    assert "+91-9876543210" not in sanitized
    assert "robert.smith@med.example.com" not in sanitized
    assert "15/08/2023" not in sanitized

    # Clinical meaning must be preserved
    assert "Type 2 Diabetes" in sanitized
    assert "HbA1c" in sanitized
    assert "8.2%" in sanitized
    assert "Metformin 500 mg" in sanitized

    # Redaction masks present
    assert "[PATIENT_ID]" in sanitized
    assert "[GOV_ID]" in sanitized
    assert "[PHONE]" in sanitized
    assert "[EMAIL]" in sanitized
    assert "[DATE]" in sanitized


def test_clinical_whitelist_protection():
    clinical_narrative = (
        "The patient was diagnosed with Hypertension and Chronic Kidney Disease. "
        "Prescribed Lisinopril 10 mg and Atorvastatin 20 mg. "
        "Negative for acute distress. Potassium was Normal at 4.2 mmol/L."
    )

    sanitized, counts, _ = deidentification_engine.deidentify(
        text=clinical_narrative,
        tenant_id="tenant_test",
        document_id="doc_test_2",
        correlation_id="corr_test_2",
    )

    # Protected medical terms must not be redacted
    assert "Hypertension" in sanitized
    assert "Chronic Kidney Disease" in sanitized
    assert "Lisinopril 10 mg" in sanitized
    assert "Atorvastatin 20 mg" in sanitized
    assert "Negative" in sanitized
    assert "Normal" in sanitized
    assert "4.2 mmol/L" in sanitized
