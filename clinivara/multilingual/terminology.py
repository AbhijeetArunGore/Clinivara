"""
Multilingual Clinical Terminology and Layperson Translation Dictionary.
Supports English, Hindi, and Marathi clinical concepts.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class MultilingualTerm(BaseModel):
    """Bilingual/multilingual clinical concept representation."""
    model_config = ConfigDict(frozen=True)

    concept_id: str
    canonical_english: str
    hindi_term: str
    hindi_explanation: str
    marathi_term: str
    marathi_explanation: str
    category: str


# Baseline curated dictionary for clinical lab reports and diagnoses
CLINICAL_TERMINOLOGY_MAP: Dict[str, MultilingualTerm] = {
    "diabetes": MultilingualTerm(
        concept_id="CONCEPT_DIABETES",
        canonical_english="Type 2 Diabetes Mellitus",
        hindi_term="मधुमेह (डायबिटीज)",
        hindi_explanation="शरीर में रक्त शर्करा (ब्लड शुगर) का स्तर सामान्य से अधिक होने की स्थिति।",
        marathi_term="मधुमेह (डायबेटीस)",
        marathi_explanation="शरीरातील रक्तातील साखरेचे प्रमाण प्रमाणापेक्षा जास्त असण्याची स्थिती.",
        category="DIAGNOSIS",
    ),
    "hypertension": MultilingualTerm(
        concept_id="CONCEPT_HYPERTENSION",
        canonical_english="Hypertension",
        hindi_term="उच्च रक्तचाप (हाई ब्लड प्रेशर)",
        hindi_explanation="रक्त वाहिकाओं में रक्त का दबाव सामान्य से अधिक होना।",
        marathi_term="उच्च रक्तदाब (हाय ब्लड प्रेशर)",
        marathi_explanation="रक्तवाहिन्यांमधील रक्ताचा दाब सामान्य मर्यादेपेक्षा जास्त असणे.",
        category="DIAGNOSIS",
    ),
    "hba1c": MultilingualTerm(
        concept_id="CONCEPT_HBA1C",
        canonical_english="Hemoglobin A1c (HbA1c)",
        hindi_term="ग्लाइकेटेड हीमोग्लोबिन (HbA1c)",
        hindi_explanation="यह जांच पिछले 2 से 3 महीनों का औसत ब्लड शुगर स्तर दर्शाती है।",
        marathi_term="ग्लायकेटेड हिमोग्लोबिन (HbA1c)",
        marathi_explanation="ही चाचणी मागील २ ते ३ महिन्यांतील रक्तातील साखरेची सरासरी पातळी दर्शवते.",
        category="LAB_TEST",
    ),
    "glucose": MultilingualTerm(
        concept_id="CONCEPT_GLUCOSE",
        canonical_english="Blood Glucose",
        hindi_term="रक्त शर्करा (ब्लड ग्लूकोज)",
        hindi_explanation="रक्त में मौजूद शर्करा की मात्रा जो शरीर को ऊर्जा देती है।",
        marathi_term="रक्तातील साखर (ग्लुकोज)",
        marathi_explanation="रक्तातील साखरेचे प्रमाण जे शरीराला ऊर्जा पुरवते.",
        category="LAB_TEST",
    ),
    "creatinine": MultilingualTerm(
        concept_id="CONCEPT_CREATININE",
        canonical_english="Serum Creatinine",
        hindi_term="सीरम क्रिएटिनिन",
        hindi_explanation="गुर्दे (किडनी) के कार्य की जांच; बढ़ा हुआ स्तर गुर्दे पर दबाव दर्शा सकता है।",
        marathi_term="सिरम क्रिएटिनिन",
        marathi_explanation="मूत्रपिंडाच्या (किडनीच्या) कार्याची तपासणी; वाढलेली पातळी किडनीवरील ताण दर्शवू शकते.",
        category="LAB_TEST",
    ),
    "hemoglobin": MultilingualTerm(
        concept_id="CONCEPT_HEMOGLOBIN",
        canonical_english="Hemoglobin",
        hindi_term="हीमोग्लोबिन",
        hindi_explanation="लाल रक्त कोशिकाओं में मौजूद प्रोटीन जो शरीर में ऑक्सीजन पहुंचाता है।",
        marathi_term="हिमोग्लोबिन",
        marathi_explanation="लाल रक्तपेशींमधील प्रथिन जे संपूर्ण शरीरात ऑक्सिजन वाहून नेते.",
        category="LAB_TEST",
    ),
    "cholesterol": MultilingualTerm(
        concept_id="CONCEPT_CHOLESTEROL",
        canonical_english="Total Cholesterol",
        hindi_term="कुल कोलेस्ट्रॉल (वसा)",
        hindi_explanation="रक्त में मौजूद चर्बी (लिपिड); अधिक मात्रा हृदय स्वास्थ्य को प्रभावित कर सकती है।",
        marathi_term="एकूण कोलेस्टेरॉल",
        marathi_explanation="रक्तातील चरबीचे प्रमाण; अधिक पातळी हृदयस्वास्थ्यावर परिणाम करू शकते.",
        category="LAB_TEST",
    ),
    "normal": MultilingualTerm(
        concept_id="CONCEPT_NORMAL",
        canonical_english="Normal",
        hindi_term="सामान्य",
        hindi_explanation="मानक स्वस्थ सीमा के भीतर।",
        marathi_term="सामान्य",
        marathi_explanation="मानक निरोगी मर्यादेत.",
        category="STATUS",
    ),
    "high": MultilingualTerm(
        concept_id="CONCEPT_HIGH",
        canonical_english="High / Elevated",
        hindi_term="उच्च / बढ़ा हुआ",
        hindi_explanation="संदर्भ सीमा से अधिक।",
        marathi_term="जास्त / वाढलेले",
        marathi_explanation="संदर्भ मर्यादेपेक्षा जास्त.",
        category="STATUS",
    ),
    "low": MultilingualTerm(
        concept_id="CONCEPT_LOW",
        canonical_english="Low / Decreased",
        hindi_term="निम्न / कम",
        hindi_explanation="संदर्भ सीमा से कम।",
        marathi_term="कमी / घटलेले",
        marathi_explanation="संदर्भ मर्यादेपेक्षा कमी.",
        category="STATUS",
    ),
}


class ClinicalTerminologyService:
    """Provides multilingual mapping and explanations for clinical findings."""

    @staticmethod
    def get_term(concept_key: str) -> Optional[MultilingualTerm]:
        return CLINICAL_TERMINOLOGY_MAP.get(concept_key.lower().strip())

    @staticmethod
    def translate_concept(concept_key: str, target_language: str) -> str:
        term = CLINICAL_TERMINOLOGY_MAP.get(concept_key.lower().strip())
        if not term:
            return concept_key
        if target_language == "hi":
            return term.hindi_term
        elif target_language == "mr":
            return term.marathi_term
        return term.canonical_english

    @staticmethod
    def explain_concept(concept_key: str, target_language: str) -> Optional[str]:
        term = CLINICAL_TERMINOLOGY_MAP.get(concept_key.lower().strip())
        if not term:
            return None
        if target_language == "hi":
            return term.hindi_explanation
        elif target_language == "mr":
            return term.marathi_explanation
        return term.canonical_english


ClinicalTerminologyTrilingual = ClinicalTerminologyService
clinical_terminology = ClinicalTerminologyService()
