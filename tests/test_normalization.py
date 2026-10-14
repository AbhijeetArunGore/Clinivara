"""
Unit tests for text normalization, clinical data quality, and section extraction.
"""

from clinivara.normalization.quality_validator import data_quality_validator
from clinivara.normalization.text_cleaner import text_cleaner


def test_unicode_and_whitespace_normalization():
    raw = "Patient\t  reported\r\n\r\n\r\nsevere headache.\x0cLine after form feed.\n"
    cleaned = text_cleaner.clean_text(raw)

    assert "\r" not in cleaned
    assert "\x0c" not in cleaned
    assert "Patient" in cleaned
    assert "severe headache." in cleaned


def test_clinical_symbol_and_unit_preservation():
    raw_clinical = (
        "WBC count: 11.2 cells/mcL\n"
        "HbA1c: 8.5%\n"
        "Blood Glucose: > 250 mg/dL\n"
        "Creatinine: ≤ 1.2 mg/dL\n"
        "Dosage: Metformin 500 mg PO BID\n"
        "Electrolytes: K+ 4.1 mmol/L, Na 138 mEq/L\n"
        "Blood Pressure: 120/80 mmHg"
    )

    cleaned = text_cleaner.clean_text(raw_clinical)
    preserved, warnings, metrics = data_quality_validator.validate_preservation(raw_clinical, cleaned)

    assert preserved is True
    assert len(warnings) == 0
    assert ">" in cleaned
    assert "≤" in cleaned
    assert "8.5%" in cleaned
    assert "500 mg" in cleaned
    assert "mmol/L" in cleaned


def test_clinical_section_parsing():
    report = (
        "PREAMBLE NOTE\n"
        "CHIEF COMPLAINT:\n"
        "Chest pain on exertion.\n\n"
        "PAST MEDICAL HISTORY:\n"
        "Hypertension, CAD.\n\n"
        "MEDICATIONS:\n"
        "Aspirin 81 mg daily.\n\n"
        "PLAN:\n"
        "Schedule echocardiogram."
    )

    sections = text_cleaner.extract_sections(report)
    titles = [s.title for s in sections]

    assert "CHIEF COMPLAINT" in titles
    assert "PAST MEDICAL HISTORY" in titles
    assert "MEDICATIONS" in titles
    assert "PLAN" in titles

    med_sec = next(s for s in sections if s.title == "MEDICATIONS")
    assert "Aspirin 81 mg" in med_sec.content
