"""
Automated unit and integration tests for multilingual processing:
- Language and script detection.
- Devanagari Unicode normalization.
- Hindi vs Marathi lexical disambiguation.
- Clinical translation with entity preservation.
- Language registry capability reporting.
"""

import pytest

from clinivara.multilingual.language_detection import LanguageDetector
from clinivara.multilingual.language_registry import LanguageRegistry
from clinivara.multilingual.terminology import ClinicalTerminologyTrilingual
from clinivara.multilingual.translation import MultilingualTranslator
from clinivara.multilingual.unicode_normalizer import DevanagariUnicodeNormalizer


def test_language_detection_english():
    detector = LanguageDetector()
    text = "Complete Blood Count: Hemoglobin 14.2 g/dL, Platelet count 250,000 /cumm."
    res = detector.detect_language(text)
    assert res.detected_language == "en"
    assert res.confidence >= 0.85
    assert not res.is_uncertain


def test_language_detection_hindi():
    detector = LanguageDetector()
    text = "रक्त जांच रिपोर्ट: मरीज का हीमोग्लोबिन सामान्य है। कोई गंभीर समस्या नहीं है।"
    res = detector.detect_language(text)
    assert res.detected_language == "hi"
    assert res.confidence >= 0.80
    assert "Devanagari" in res.script_distribution


def test_language_detection_marathi_disambiguation():
    detector = LanguageDetector()
    # Contains letter 'ळ' and Marathi marker words 'आहे', 'तपासणी'
    text = "रुग्ण तपासणी अहवाल: हिमोग्लोबिन १२.५ g/dL आहे. पुढील काळजी घेणे आवश्यक आहे."
    res = detector.detect_language(text)
    assert res.detected_language == "mr"
    assert res.confidence >= 0.80


def test_language_detection_mixed_script():
    detector = LanguageDetector()
    text = "Patient report: हीमोग्लोबिन 13.5 g/dL, Fasting blood sugar सामान्य है।"
    res = detector.detect_language(text)
    assert res.is_mixed_script
    assert "Latin" in res.script_distribution
    assert "Devanagari" in res.script_distribution


def test_language_detection_empty_input():
    detector = LanguageDetector()
    res = detector.detect_language("   ")
    assert res.detected_language == "unknown"
    assert res.is_uncertain


def test_devanagari_unicode_normalizer_matra_and_indic_digits():
    normalizer = DevanagariUnicodeNormalizer()
    # 'क ा' has an OCR space between consonant and matra; '८.४' is Indic digits
    raw = "रक्त तपासणी: हीमोग्लोबिन ८.४ g/dL क ा निष्कर्ष।"
    normalized = normalizer.normalize(raw)
    
    # Matra merged
    assert "का" in normalized
    # Indic digits translated to standard Arabic digits
    assert "8.4" in normalized


def test_devanagari_danda_normalization():
    normalizer = DevanagariUnicodeNormalizer()
    text = "पहला वाक्य। दूसरा वाक्य॥"
    normalized = normalizer.normalize(text)
    assert "।" not in normalized
    assert "॥" not in normalized
    assert "." in normalized


def test_clinical_translation_preserves_medication_and_numbers():
    translator = MultilingualTranslator()
    text = "Patient is prescribed Metformin 500 mg PO BID. Blood pressure is 130/80 mmHg."
    res = translator.translate(text, source_language="en", target_language="hi")
    
    assert res.target_language == "hi"
    # Clinical units and medications must not be mangled
    assert "Metformin" in res.translated_text
    assert "500 mg" in res.translated_text
    assert "130/80" in res.translated_text
    assert any("Metformin" in t for t in res.preserved_terms)


def test_clinical_translation_marathi():
    translator = MultilingualTranslator()
    text = "Fasting glucose is 95 mg/dL which is normal."
    res = translator.translate(text, source_language="en", target_language="mr")
    
    assert res.target_language == "mr"
    assert "95 mg/dL" in res.translated_text
    assert "सामान्य" in res.translated_text


def test_language_registry_supported_languages():
    registry = LanguageRegistry()
    assert registry.is_supported("en")
    assert registry.is_supported("hi")
    assert registry.is_supported("mr")
    assert not registry.is_supported("fr")
    
    hi_meta = registry.get("hi")
    assert hi_meta is not None
    assert hi_meta.script == "Devanagari"
