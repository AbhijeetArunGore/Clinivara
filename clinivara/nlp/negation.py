"""
Multilingual clinical negation, uncertainty, and temporality detector.
Supports English, Hindi, and Marathi clinical context without clinical corruption.
"""

import re
from typing import NamedTuple, Optional, Tuple


class AssertionAnalysis(NamedTuple):
    is_negated: bool
    is_uncertain: bool
    temporality: str
    matched_trigger: Optional[str] = None

# Pre-compiled contextual triggers across English, Hindi, and Marathi
NEGATION_PATTERNS = [
    # English
    r"\b(?:no\s+evidence\s+of|negative\s+for|rules?\s+out|ruled\s+out|denies|without|absence\s+of|not\s+detected|no\s+history\s+of|unremarkable)\b",
    r"\b(?:no|not|none)\b",
    # Hindi
    r"(?:कोई\s+प्रमाण\s+नहीं|नकारात्मक|नहीं\s+पाया\s+गया|अनुपस्थित|शिकायत\s+नहीं|नहीं\s+है|नहीं)",
    # Marathi
    r"(?:कोणताही\s+पुरावा\s+नाही|नकारात्मक|आढळले\s+नाही|लक्षणे\s+नाहीत|नाही|नाहीत|दिसून\s+आले\s+नाही)",
]

UNCERTAINTY_PATTERNS = [
    # English
    r"\b(?:possible|suspected|borderline|likely|equivocal|cannot\s+be\s+excluded|rule\s+out|probable)\b",
    # Hindi
    r"(?:संभावित|संशयित|संदेहास्पद|आशंका)",
    # Marathi
    r"(?:संभाव्य|संशयित|शक्यता|संशय)",
]

TEMPORALITY_PATTERNS = [
    # Past / Historical
    (r"\b(?:history\s+of|past|previously|prior|resolved|former)\b", "PAST"),
    (r"(?:पिछला|इतिहास|पूर्व|पहले)", "PAST"),
    (r"(?:मागील|पूर्वी|भूतकाळात)", "PAST"),
    # Family History
    (r"\b(?:family\s+history|maternal|paternal)\b", "FAMILY"),
    (r"(?:पारिवारिक\s+इतिहास|कुटुंबात)", "FAMILY"),
]

COMPILED_NEGATIONS = re.compile("|".join(NEGATION_PATTERNS), re.IGNORECASE)
COMPILED_UNCERTAINTY = re.compile("|".join(UNCERTAINTY_PATTERNS), re.IGNORECASE)


class ClinicalNegationDetector:
    """Detects negated findings, diagnostic uncertainty, and temporal context."""

    @staticmethod
    def analyze_assertion(sentence: str) -> Tuple[bool, bool, str, Optional[str]]:
        """
        Analyzes a sentence or clinical phrase for negation, uncertainty, and temporality.
        Returns:
            (is_negated, is_uncertain, temporality, matched_trigger)
        """
        if not sentence or not sentence.strip():
            return False, False, "CURRENT", None

        # Check Negation
        neg_match = COMPILED_NEGATIONS.search(sentence)
        is_negated = neg_match is not None
        trigger = neg_match.group(0) if neg_match else None

        # Check Uncertainty
        unc_match = COMPILED_UNCERTAINTY.search(sentence)
        is_uncertain = unc_match is not None
        if not trigger and unc_match:
            trigger = unc_match.group(0)

        # Check Temporality
        temporality = "CURRENT"
        for pat, temp_label in TEMPORALITY_PATTERNS:
            if re.search(pat, sentence, re.IGNORECASE):
                temporality = temp_label
                break

        return AssertionAnalysis(
            is_negated=is_negated,
            is_uncertain=is_uncertain,
            temporality=temporality,
            matched_trigger=trigger,
        )


clinical_negation_detector = ClinicalNegationDetector()
