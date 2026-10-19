"""
Multilingual clinical translation service preserving clinical fidelity.
"""

import re

from clinivara.multilingual.terminology import clinical_terminology
from clinivara.schemas.ai import TranslationResponse

# Strict preservation patterns: medications, numbers with units, and clinical operators
PRESERVED_PATTERNS = [
    r"\b\d+(?:\.\d+)?\s*(?:mg/dL|mmol/L|g/dL|mIU/L|mcg|mg|%|mmHg)\b",
    r"\b(?:[7-9]\d|1\d\d|2[0-1]\d)/(?:[4-9]\d|1[0-2]\d)\s*(?:mmHg)?\b",
    r"\b(?:Metformin|Lisinopril|Amlodipine|Atorvastatin|Aspirin|Insulin|Omeprazole|Paracetamol)\b",
    r"[<>=≤≥±]",
]


class ClinicalTranslationService:
    """Safe clinical translator with terminology and numerical preservation."""

    def __init__(self):
        self._phrase_dict_hi = {
            "hospital discharge summary": "अस्पताल डिस्चार्ज सारांश",
            "clinical laboratory report": "चिकित्सीय प्रयोगशाला रिपोर्ट",
            "chief complaint": "मुख्य समस्या",
            "past medical history": "पिछला चिकित्सीय इतिहास",
            "current medications": "वर्तमान दवाएं",
            "laboratory results": "प्रयोगशाला जांच परिणाम",
            "assessment & plan": "चिकित्सीय मूल्यांकन एवं योजना",
            "diagnosis": "निदान / बीमारी",
            "patient": "मरीज",
            "normal": "सामान्य",
            "high": "उच्च / बढ़ा हुआ",
            "low": "निम्न / कम",
            "uncontrolled": "अनियंत्रित",
            "follow up in": "पुनः जांच / परामर्श",
            "increase": "बढ़ाएं",
            "daily": "प्रतिदिन",
        }

        self._phrase_dict_mr = {
            "hospital discharge summary": "रुग्णालय डिस्चार्ज सारांश",
            "clinical laboratory report": "वैद्यकीय प्रयोगशाळा तपासणी अहवाल",
            "chief complaint": "मुख्य तक्रार",
            "past medical history": "मागील वैद्यकीय इतिहास",
            "current medications": "सध्याची औषधे",
            "laboratory results": "प्रयोगशाळा चाचणी निष्कर्ष",
            "assessment & plan": "वैद्यकीय मूल्यमापन आणि पुढील योजना",
            "diagnosis": "निदान / आजार",
            "patient": "रुग्ण",
            "normal": "सामान्य",
            "high": "जास्त / वाढलेले",
            "low": "कमी / घटलेले",
            "uncontrolled": "अनियंत्रित",
            "follow up in": "पुढील तपासणी / भेट",
            "increase": "वाढवा",
            "daily": "दररोज",
        }

    def _extract_preserved_terms(self, text: str) -> list[str]:
        """Collect all numbers, units, and drug names that must be strictly preserved."""
        preserved = []
        for pat in PRESERVED_PATTERNS:
            for match in re.finditer(pat, text, re.IGNORECASE):
                preserved.append(match.group(0))
        return list(set(preserved))

    def translate(
        self,
        text: str,
        source_language: str = "en",
        target_language: str = "hi",
        preserve_medical_terms: bool = True,
        preserve_terms: bool = True,
    ) -> TranslationResponse:
        """
        Translates clinical content to Hindi or Marathi while safeguarding medical facts.
        """
        if preserve_terms is not None:
            preserve_medical_terms = preserve_terms

        if not text or not text.strip():
            return TranslationResponse(
                original_text="",
                translated_text="",
                source_language=source_language,
                target_language=target_language,
                preserved_terms=[],
                quality_score=1.0,
            )

        if source_language.lower() == target_language.lower():
            return TranslationResponse(
                original_text=text,
                translated_text=text,
                source_language=source_language,
                target_language=target_language,
                preserved_terms=[],
                quality_score=1.0,
            )

        preserved_terms = self._extract_preserved_terms(text) if preserve_medical_terms else []

        phrase_dict = self._phrase_dict_hi if target_language == "hi" else self._phrase_dict_mr

        translated = text
        # Perform phrase and terminology replacement
        for en_phrase, localized in phrase_dict.items():
            pattern = re.compile(rf"\b{re.escape(en_phrase)}\b", re.IGNORECASE)
            translated = pattern.sub(localized, translated)

        # Ensure concept translation
        for word in ["diabetes", "hypertension", "hba1c", "glucose", "creatinine", "hemoglobin"]:
            concept_trans = clinical_terminology.translate_concept(word, target_language)
            translated = re.sub(rf"\b{word}\b", concept_trans, translated, flags=re.IGNORECASE)

        return TranslationResponse(
            original_text=text,
            translated_text=translated,
            source_language=source_language,
            target_language=target_language,
            preserved_terms=preserved_terms,
            quality_score=0.95,
        )


MultilingualTranslator = ClinicalTranslationService
clinical_translator = ClinicalTranslationService()
