"""
Automated unit and integration tests for clinical fact extraction:
- Document classification.
- Section and table parsing.
- LOINC terminology mapping.
- UCUM unit validation and derived status calculation.
- Negation and temporality preservation.
"""

import pytest

from clinivara.clinical.document_classifier import ClinicalDocumentClassifier
from clinivara.clinical.extraction.extractor import ClinicalExtractor
from clinivara.clinical.table_extractor import LabTableExtractor
from clinivara.clinical.terminology.loinc_adapter import LOINCAdapter
from clinivara.clinical.unit_validator import UnitValidator
from clinivara.nlp.negation import ClinicalNegationDetector


def test_document_classification_cbc():
    classifier = ClinicalDocumentClassifier()
    text = "COMPLETE BLOOD COUNT REPORT\nHemoglobin: 13.8 g/dL\nWBC: 6500 /cumm\nPlatelets: 250000"
    res = classifier.classify(text)
    assert res.category == "HEMATOLOGY_CBC"
    assert res.confidence >= 0.85
    assert res.detected_language == "en"


def test_document_classification_biochemistry():
    classifier = ClinicalDocumentClassifier()
    text = "BIOCHEMISTRY EXAMINATION REPORT\nFasting Blood Glucose: 110 mg/dL\nSerum Creatinine: 0.9 mg/dL"
    res = classifier.classify(text)
    assert res.category == "BIOCHEMISTRY_METABOLIC"


def test_table_extractor_key_value_with_reference():
    extractor = LabTableExtractor()
    text = (
        "Fasting Blood Glucose: 165 mg/dL (Reference: 70 - 99 mg/dL)\n"
        "Serum Creatinine: 1.1 mg/dL (0.7 - 1.3 mg/dL)\n"
        "Total Cholesterol: < 200 mg/dL"
    )
    observations = extractor.extract_observations(text)
    assert len(observations) == 3

    glucose = next(o for o in observations if "glucose" in o.test_name.lower())
    assert glucose.numeric_value == 165.0
    assert glucose.original_unit == "mg/dL"
    assert glucose.reference_range is not None
    assert glucose.reference_range.low == 70.0
    assert glucose.reference_range.high == 99.0
    assert glucose.derived_status == "HIGH"
    assert glucose.is_abnormal

    chol = next(o for o in observations if "cholesterol" in o.test_name.lower())
    assert chol.comparator == "<"
    assert chol.numeric_value == 200.0


def test_table_extractor_tabular_columns():
    extractor = LabTableExtractor()
    text = (
        "TEST NAME\t\tRESULT\tUNIT\tREFERENCE INTERVAL\n"
        "Hemoglobin\t\t14.2\tg/dL\t13.0 - 17.0\n"
        "Platelet Count\t220000\t/cumm\t150000 - 450000"
    )
    observations = extractor.extract_observations(text)
    assert len(observations) == 2
    hemo = next(o for o in observations if "hemo" in o.test_name.lower())
    assert hemo.numeric_value == 14.2
    assert hemo.original_unit == "g/dL"
    assert hemo.reference_range.low == 13.0
    assert hemo.derived_status == "NORMAL"


def test_loinc_adapter_mapping():
    adapter = LOINCAdapter()
    concept = adapter.map_test_name("Fasting Blood Sugar")
    assert concept is not None
    assert concept.loinc_code == "1558-6"
    assert concept.standard_unit == "mg/dL"

    # Hindi test name
    hindi_concept = adapter.map_test_name("हीमोग्लोबिन")
    assert hindi_concept is not None
    assert hindi_concept.loinc_code == "718-7"


def test_unit_validator_standardization_and_evaluation():
    validator = UnitValidator()
    # UCUM standardization
    assert validator.standardize_unit("G/DL") == "g/dL"
    assert validator.standardize_unit("MG/DL") == "mg/dL"

    # Out of range evaluation
    status, is_abn = validator.evaluate_derived_status(value=180.0, low=70.0, high=99.0)
    assert status == "HIGH"
    assert is_abn

    status_low, is_abn_low = validator.evaluate_derived_status(value=50.0, low=70.0, high=99.0)
    assert status_low == "LOW"
    assert is_abn_low

    status_normal, is_abn_norm = validator.evaluate_derived_status(value=85.0, low=70.0, high=99.0)
    assert status_normal == "NORMAL"
    assert not is_abn_norm


def test_negation_and_uncertainty_detector():
    detector = ClinicalNegationDetector()
    
    # English negation
    neg_en = detector.analyze_assertion("Patient has no evidence of acute chest pain or fever.")
    assert neg_en.is_negated
    assert not neg_en.is_uncertain

    # English uncertainty
    unc_en = detector.analyze_assertion("Possible early diabetic nephropathy to be investigated.")
    assert unc_en.is_uncertain
    assert not unc_en.is_negated

    # Hindi negation
    neg_hi = detector.analyze_assertion("मरीज को सांस लेने में कोई तकलीफ नहीं है।")
    assert neg_hi.is_negated

    # Marathi negation
    neg_mr = detector.analyze_assertion("रुग्णाला खोकल्याचा कोणताही त्रास नाही.")
    assert neg_mr.is_negated
