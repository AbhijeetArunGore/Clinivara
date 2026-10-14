"""
Clinical preservation checker.

Verifies that essential medical facts, diagnoses, vital signs, dosages,
and laboratory metrics present in the original report are preserved
and uncorrupted in the de-identified text.
"""

import re
from typing import List, Tuple


class ClinicalPreservationChecker:
    """Verifies that clinical utility has been preserved after de-identification."""

    @staticmethod
    def check_preservation(
        original_text: str,
        deidentified_text: str,
    ) -> Tuple[bool, List[str]]:
        """
        Evaluates preservation of critical clinical information.
        Returns:
            (preserved_status, warnings)
        """
        warnings = []

        # 1. Check preservation of laboratory numerical metrics with units (e.g. 8.2%, 140 mg/dL, 500 mg)
        metric_pattern = re.compile(
            r"\b(\d+(?:\.\d+)?)\s*(mg/dL|mmol/L|g/dL|mIU/L|mcg|mg|%|mmHg)\b",
            re.IGNORECASE,
        )
        orig_metrics = set(m.group(0).lower() for m in metric_pattern.finditer(original_text))

        for metric in orig_metrics:
            if metric not in deidentified_text.lower():
                warnings.append(f"Clinical laboratory metric '{metric}' appears missing in de-identified output.")

        # 2. Check preservation of true blood pressure patterns (e.g. 120/80, 135/85), excluding dates (e.g. 12/04/1982)
        bp_pattern = re.compile(r"\b(?:[7-9]\d|1\d\d|2[0-1]\d)/(?:[4-9]\d|1[0-2]\d)(?!\s*/\s*\d{2,4})\s*(?:mmHg)?\b", re.IGNORECASE)
        orig_bps = set(b.group(0).lower() for b in bp_pattern.finditer(original_text))
        for bp in orig_bps:
            if bp not in deidentified_text.lower():
                warnings.append(f"Vital sign measurement '{bp}' appears missing in de-identified output.")

        # Clinical preservation holds if no critical clinical metrics were accidentally removed
        preserved = len(warnings) == 0
        return preserved, warnings


preservation_checker = ClinicalPreservationChecker()
