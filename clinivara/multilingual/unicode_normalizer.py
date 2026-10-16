"""
Conservative Unicode and script normalizer for Devanagari (Hindi and Marathi) clinical text.
"""

import re
import unicodedata


class DevanagariUnicodeNormalizer:
    """Conservative normalizer for Devanagari and mixed Indic-Latin medical documents."""

    @staticmethod
    def normalize_devanagari(text: str) -> str:
        """
        Normalizes Devanagari script:
        - Canonical Unicode NFC normalization.
        - Fixes OCR matra spacing artifacts (e.g. 'क ा' -> 'का').
        - Standardizes Devanagari danda punctuation.
        - Preserves clinical numbers, decimals, and units intact.
        """
        if not text:
            return ""

        # 1. Unicode NFC canonical decomposition followed by canonical composition
        normalized = unicodedata.normalize("NFC", text)

        # 2. Fix OCR space split between Devanagari consonant and vowel matra (U+093E to U+094C)
        # E.g. 'क ा' -> 'का', 'म ू' -> 'मू'
        matra_regex = re.compile(r"([\u0915-\u0939])\s+([\u093E-\u094C\u0902\u0903\u094D])")
        normalized = matra_regex.sub(r"\1\2", normalized)

        # 3. Standardize Devanagari Danda (। U+0964) and Double Danda (॥ U+0965)
        normalized = normalized.replace("\u0965", ".").replace("\u0964", ".")

        # 4. Standardize Indic digits (०-९ U+0966 to U+096F) to standard Arabic numerals
        # This is critical so downstream laboratory parsers do not fail on Hindi numerals (e.g. ८.४ -> 8.4)
        indic_to_arabic = str.maketrans("०१२३४५६७८९", "0123456789")
        normalized = normalized.translate(indic_to_arabic)

        # 5. Clean repeated spaces without destroying tab column separators
        lines = [re.sub(r" {2,}", " ", line).strip() for line in normalized.splitlines()]
        return "\n".join(lines).strip()

    @classmethod
    def normalize(cls, text: str) -> str:
        return cls.normalize_devanagari(text)


devanagari_normalizer = DevanagariUnicodeNormalizer()
