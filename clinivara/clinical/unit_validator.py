"""
Clinical unit validator and standard UCUM representation adapter.
"""

import re
from typing import Optional, Tuple

VALID_CLINICAL_UNITS = {
    "mg/dl": "mg/dL",
    "mmol/l": "mmol/L",
    "g/dl": "g/dL",
    "miu/l": "mIU/L",
    "iu/l": "IU/L",
    "mcg": "mcg",
    "µg": "mcg",
    "mg": "mg",
    "g": "g",
    "%": "%",
    "mmhg": "mmHg",
    "cells/mcl": "cells/mcL",
    "cells/cumm": "cells/mcL",
    "ng/ml": "ng/mL",
    "meq/l": "mEq/L",
}


class UnitValidator:
    """Validates and standardizes clinical measurement units."""

    @staticmethod
    def standardize_unit(raw_unit: Optional[str]) -> Optional[str]:
        if not raw_unit:
            return None
        cleaned = raw_unit.strip().lower()
        return VALID_CLINICAL_UNITS.get(cleaned, raw_unit.strip())

    @staticmethod
    def validate_syntax(unit: str) -> bool:
        if not unit:
            return False
        return unit.strip().lower() in VALID_CLINICAL_UNITS

    @staticmethod
    def evaluate_derived_status(
        numeric_val: Optional[float] = None,
        ref_low: Optional[float] = None,
        ref_high: Optional[float] = None,
        value: Optional[float] = None,
        low: Optional[float] = None,
        high: Optional[float] = None,
    ) -> Tuple[str, bool]:
        """
        Derives clinical status flag based on reported reference interval.
        Returns:
            (status: NORMAL | HIGH | LOW | UNKNOWN, is_abnormal: bool)
        """
        if value is not None:
            numeric_val = value
        if low is not None:
            ref_low = low
        if high is not None:
            ref_high = high

        if numeric_val is None or (ref_low is None and ref_high is None):
            return "UNKNOWN", False

        if ref_low is not None and numeric_val < ref_low:
            return "LOW", True
        if ref_high is not None and numeric_val > ref_high:
            return "HIGH", True

        return "NORMAL", False


unit_validator = UnitValidator()
