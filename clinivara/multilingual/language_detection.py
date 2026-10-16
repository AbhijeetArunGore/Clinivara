"""
Multilingual language and script detector for English, Hindi, and Marathi clinical documents.
"""

import re
from typing import Dict, List, Literal, Tuple
from pydantic import BaseModel, ConfigDict, Field


class LanguageDetectionResult(BaseModel):
    """Result of language and script identification."""
    model_config = ConfigDict(frozen=True)

    primary_language: Literal["en", "hi", "mr", "unknown"]
    confidence: float = Field(ge=0.0, le=1.0)
    secondary_languages: List[str] = Field(default_factory=list)
    is_mixed_script: bool = False
    script_distribution: Dict[str, float] = Field(default_factory=dict)
    detection_method: str = "SCRIPT_AND_LEXICAL_HEURISTICS"
    is_uncertain: bool = False

    @property
    def detected_language(self) -> str:
        return self.primary_language


# Lexical markers for disambiguating Devanagari text
MARATHI_MARKERS = {
    "आहे", "नाही", "रुग्ण", "तपासणी", "दिनांक", "रक्त", "वय", "निष्कर्ष",
    "उपचार", "तक्रार", "केले", "होते", "येथे", "नाव", "तसेच", "औषध", "लक्षणे"
}

HINDI_MARKERS = {
    "है", "नहीं", "मरीज", "जांच", "दिनांक", "रक्त", "उम्र", "उपचार",
    "समस्या", "था", "थी", "किया", "गया", "नाम", "दवा", "लक्षण", "कृपया"
}


class LanguageDetector:
    """Lightweight deterministic script and lexical language detector for healthcare text."""

    @staticmethod
    def detect_language(text: str) -> LanguageDetectionResult:
        """
        Identifies whether text is English, Hindi, Marathi, or mixed-script.
        Handles Devanagari disambiguation via the letter 'ळ' and regional clinical stop-words.
        """
        if not text or not text.strip():
            return LanguageDetectionResult(
                primary_language="unknown",
                confidence=0.0,
                is_uncertain=True,
                detection_method="EMPTY_INPUT",
            )

        # 1. Count script characters
        latin_count = 0
        devanagari_count = 0
        other_count = 0

        for ch in text:
            code = ord(ch)
            if (65 <= code <= 90) or (97 <= code <= 122):
                latin_count += 1
            elif 0x0900 <= code <= 0x097F:
                devanagari_count += 1
            elif not ch.isspace() and not ch.isdigit() and ch not in ".,;:!?-/<>()[]{}'\"":
                other_count += 1

        total_alpha = latin_count + devanagari_count + other_count
        if total_alpha == 0:
            return LanguageDetectionResult(
                primary_language="en",
                confidence=0.50,
                is_uncertain=True,
                detection_method="NO_ALPHABETIC_CHARS",
            )

        latin_ratio = latin_count / total_alpha
        deva_ratio = devanagari_count / total_alpha
        script_dist = {
            "Latin": round(latin_ratio, 3),
            "Devanagari": round(deva_ratio, 3),
        }

        # 2. Pure Latin script -> English
        if deva_ratio < 0.05 and latin_ratio >= 0.70:
            return LanguageDetectionResult(
                primary_language="en",
                confidence=round(min(1.0, latin_ratio), 2),
                secondary_languages=[],
                is_mixed_script=False,
                script_distribution=script_dist,
                detection_method="LATIN_DOMINANT",
            )

        # 3. Devanagari script present: Disambiguate Hindi vs Marathi
        is_mixed = latin_ratio >= 0.15 and deva_ratio >= 0.20

        # Check for Marathi unique character 'ळ' (U+0933)
        has_marathi_l = "\u0933" in text

        # Tokenize Devanagari words
        words = re.findall(r"[\u0900-\u097F]+", text)
        word_set = set(words)

        marathi_hits = len(word_set.intersection(MARATHI_MARKERS))
        hindi_hits = len(word_set.intersection(HINDI_MARKERS))

        if has_marathi_l:
            marathi_hits += 2

        if marathi_hits > hindi_hits or (marathi_hits > 0 and has_marathi_l):
            primary = "mr"
            confidence = min(0.95, 0.65 + (marathi_hits * 0.08))
            secondary = ["en"] if is_mixed else []
        elif hindi_hits > marathi_hits:
            primary = "hi"
            confidence = min(0.95, 0.65 + (hindi_hits * 0.08))
            secondary = ["en"] if is_mixed else []
        elif deva_ratio >= 0.50:
            # Default to Hindi if general Devanagari without specific Marathi markers
            primary = "hi"
            confidence = 0.70
            secondary = ["en"] if is_mixed else []
        else:
            primary = "en"
            confidence = 0.75
            secondary = ["hi"] if deva_ratio >= 0.10 else []

        return LanguageDetectionResult(
            primary_language=primary,
            confidence=round(confidence, 2),
            secondary_languages=secondary,
            is_mixed_script=is_mixed,
            script_distribution=script_dist,
            detection_method="DEVANAGARI_LEXICAL_ANALYSIS",
            is_uncertain=confidence < 0.60,
        )


language_detector = LanguageDetector()
