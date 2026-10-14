"""
Presidio custom recognizers for clinical identifiers, MRNs, and Indian health documents.
"""

from typing import List
from clinivara.deidentification.recognizers.patterns import (
    AADHAAR_CONTEXT,
    AADHAAR_REGEX,
    ABHA_CONTEXT,
    ABHA_NUMBER_REGEX,
    DOCTOR_CONTEXT,
    DOCTOR_NAME_PREFIX_REGEX,
    HOSPITAL_MRN_REGEX,
    INDIAN_PHONE_REGEX,
    MRN_CONTEXT,
    PAN_CONTEXT,
    PAN_REGEX,
    PHONE_CONTEXT,
)


def build_custom_presidio_recognizers() -> List[object]:
    """
    Construct Presidio PatternRecognizer instances for clinical entities.
    """
    try:
        from presidio_analyzer import Pattern, PatternRecognizer
    except ImportError:
        # If presidio is not yet imported/available
        return []

    recognizers = []

    # 1. Hospital MRN / UHID Recognizer
    mrn_pattern = Pattern(name="hospital_mrn_pattern", regex=HOSPITAL_MRN_REGEX, score=0.85)
    mrn_recognizer = PatternRecognizer(
        supported_entity="PATIENT_ID",
        patterns=[mrn_pattern],
        context=MRN_CONTEXT,
        name="HospitalMRNRecognizer",
    )
    recognizers.append(mrn_recognizer)

    # 2. Indian Aadhaar Recognizer
    aadhaar_pattern = Pattern(name="aadhaar_pattern", regex=AADHAAR_REGEX, score=0.80)
    aadhaar_recognizer = PatternRecognizer(
        supported_entity="GOV_ID",
        patterns=[aadhaar_pattern],
        context=AADHAAR_CONTEXT,
        name="AadhaarRecognizer",
    )
    recognizers.append(aadhaar_recognizer)

    # 3. Indian PAN Card Recognizer
    pan_pattern = Pattern(name="pan_pattern", regex=PAN_REGEX, score=0.85)
    pan_recognizer = PatternRecognizer(
        supported_entity="GOV_ID",
        patterns=[pan_pattern],
        context=PAN_CONTEXT,
        name="PanCardRecognizer",
    )
    recognizers.append(pan_recognizer)

    # 4. ABHA Number Recognizer
    abha_pattern = Pattern(name="abha_pattern", regex=ABHA_NUMBER_REGEX, score=0.85)
    abha_recognizer = PatternRecognizer(
        supported_entity="PATIENT_ID",
        patterns=[abha_pattern],
        context=ABHA_CONTEXT,
        name="AbhaIdRecognizer",
    )
    recognizers.append(abha_recognizer)

    # 5. Indian Phone Number Recognizer
    phone_pattern = Pattern(name="indian_phone_pattern", regex=INDIAN_PHONE_REGEX, score=0.75)
    phone_recognizer = PatternRecognizer(
        supported_entity="PHONE_NUMBER",
        patterns=[phone_pattern],
        context=PHONE_CONTEXT,
        name="IndianPhoneRecognizer",
    )
    recognizers.append(phone_recognizer)

    # 6. Doctor Name Prefix Recognizer
    doc_pattern = Pattern(name="doctor_prefix_pattern", regex=DOCTOR_NAME_PREFIX_REGEX, score=0.85)
    doc_recognizer = PatternRecognizer(
        supported_entity="PERSON",
        patterns=[doc_pattern],
        context=DOCTOR_CONTEXT,
        name="DoctorNameRecognizer",
    )
    recognizers.append(doc_recognizer)

    return recognizers
