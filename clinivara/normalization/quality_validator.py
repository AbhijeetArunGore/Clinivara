"""
Clinical data quality validator.

Verifies that normalization has not stripped essential clinical symbols,
units, dosages, negative signs, or comparison operators.
"""

import re
from typing import Dict, List, Tuple

# Critical clinical indicators and units that must not be corrupted
CLINICAL_UNITS = [
    r"mg(?:/dL)?",
    r"g(?:/dL)?",
    r"mmol/L",
    r"mcg|µg",
    r"mIU/L|IU/L",
    r"mEq/L",
    r"cells/mcL",
    r"%",
    r"mmHg",
]

CLINICAL_OPERATORS = [r"<", r">", r"≤", r"≥", r"±", r"=", r"-"]


class DataQualityValidator:
    """Verifies that clinical symbols, units, and numeric integrity remain uncorrupted."""

    @staticmethod
    def validate_preservation(
        original_text: str,
        cleaned_text: str,
    ) -> Tuple[bool, List[str], Dict[str, int]]:
        """
        Compare original and cleaned text for preservation of critical clinical tokens.
        """
        warnings: List[str] = []
        metrics: Dict[str, int] = {}

        # 1. Check preservation of laboratory comparison operators
        for op in CLINICAL_OPERATORS:
            orig_count = original_text.count(op)
            clean_count = cleaned_text.count(op)
            metrics[f"operator_{op}_count"] = clean_count
            if orig_count > 0 and clean_count == 0:
                warnings.append(f"Clinical operator '{op}' appears to have been lost during processing.")

        # 2. Check preservation of common clinical units
        for unit_pat in CLINICAL_UNITS:
            pattern = re.compile(rf"\b\d+(?:\.\d+)?\s*{unit_pat}\b", re.IGNORECASE)
            orig_matches = len(pattern.findall(original_text))
            clean_matches = len(pattern.findall(cleaned_text))
            metrics[f"unit_{unit_pat}_matches"] = clean_matches
            if orig_matches > 0 and clean_matches == 0:
                warnings.append(f"Clinical measurements matching unit '{unit_pat}' were lost.")

        # 3. Check for excessive null/corrupted character remnants
        replacement_count = cleaned_text.count("\ufffd")
        if replacement_count > 0:
            warnings.append(f"Cleaned text contains {replacement_count} unhandled replacement characters.")

        preserved = len(warnings) == 0
        return preserved, warnings, metrics


data_quality_validator = DataQualityValidator()
