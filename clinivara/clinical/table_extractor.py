"""
Robust clinical laboratory table and observation extractor.
Parses multi-column rows, key-value laboratory measurements, and reference intervals.
"""

import re
import uuid
from typing import List, Optional, Tuple
from clinivara.clinical.terminology.loinc_adapter import loinc_adapter
from clinivara.clinical.unit_validator import unit_validator
from clinivara.schemas.ai import ClinicalObservation, ReferenceRange

# Regex for matching clinical test observation lines
# Examples:
# HbA1c: 8.4%
# Fasting Blood Glucose: 162 mg/dL
# Serum Creatinine: 1.1 mg/dL (0.7 - 1.3)
# Total Cholesterol: 240 mg/dL [Reference: < 200]
# Hemoglobin | 14.2 | g/dL | 13.0 - 17.0
OBSERVATION_LINE_REGEX = re.compile(
    r"^[\s\*\#-]*([A-Za-z0-9\s\(\)\/\-\.\u0900-\u097F]+?)[\s\:\।\|]+([<>=≤≥]?\s*\d+(?:\.\d+)?)\s*([a-zA-Z%µ\/]+)?(?:\s*[\(\|\[](?:(?:Normal|Ref|Reference|संदर्भ|सामान्य\s*(?:सीमा|मर्यादा)?)[\s\:\-]*)?([<>=≤≥]?\s*\d+(?:\.\d+)?(?:\s*[\-\–\to]\s*\d+(?:\.\d+)?)?\s*[a-zA-Z%µ\/]*)[\)\]])?",
    re.MULTILINE,
)


class LabTableExtractor:
    """Extracts structured laboratory observations with exact evidence anchors."""

    @staticmethod
    def _parse_reference_range(ref_str: Optional[str]) -> Optional[ReferenceRange]:
        if not ref_str:
            return None
        cleaned = ref_str.strip()

        # Check for range: e.g. "4.0 - 5.6", "70 - 99"
        range_match = re.search(r"(\d+(?:\.\d+)?)\s*[\-\–\to]\s*(\d+(?:\.\d+)?)", cleaned)
        if range_match:
            low = float(range_match.group(1))
            high = float(range_match.group(2))
            return ReferenceRange(raw_text=cleaned, low=low, high=high)

        # Check for upper bound: e.g. "< 200"
        upper_match = re.search(r"[<≤]\s*(\d+(?:\.\d+)?)", cleaned)
        if upper_match:
            return ReferenceRange(raw_text=cleaned, high=float(upper_match.group(1)))

        # Check for lower bound: e.g. "> 60"
        lower_match = re.search(r"[>≥]\s*(\d+(?:\.\d+)?)", cleaned)
        if lower_match:
            return ReferenceRange(raw_text=cleaned, low=float(lower_match.group(1)))

        return ReferenceRange(raw_text=cleaned)

    @classmethod
    def extract_observations(cls, text: str, page_number: int = 1) -> List[ClinicalObservation]:
        """
        Parses text for laboratory measurements, test names, units, and reference ranges.
        """
        if not text:
            return []

        observations: List[ClinicalObservation] = []
        lines = text.splitlines()

        for line in lines:
            line_str = line.strip()
            if not line_str or len(line_str) < 5:
                continue

            # Skip clear headers/metadata lines that don't represent tests
            if any(h in line_str.lower() for h in ["patient name:", "doctor:", "date of", "phone:", "mrn:", "test name", "reference interval", "date:", "specimen:"]):
                continue

            raw_test_name = None
            raw_value_str = None
            raw_unit = None
            raw_ref_str = None

            # First, check multi-column tab/whitespace-delimited tabular line
            # E.g. "Hemoglobin \t 13.8 \t g/dL \t 12.0 - 15.5"
            parts = [p.strip() for p in re.split(r"\t+| {2,}|\|", line_str) if p.strip()]
            if len(parts) >= 3 and any(char.isdigit() for char in parts[1]):
                raw_test_name = parts[0]
                raw_value_str = parts[1]
                raw_unit = parts[2]
                if len(parts) >= 4:
                    raw_ref_str = parts[3]
            else:
                match = OBSERVATION_LINE_REGEX.match(line_str)
                if not match:
                    continue
                raw_test_name = match.group(1).strip()
                raw_value_str = match.group(2).strip()
                raw_unit = match.group(3).strip() if match.group(3) else None
                raw_ref_str = match.group(4).strip() if match.group(4) else None

            # Skip if test name is generic punctuation or too short
            if not raw_test_name or len(raw_test_name) < 2 or raw_test_name.lower() in ("test", "investigation", "parameter"):
                continue

            # Parse comparator and numeric value
            comparator = None
            numeric_val = None
            comp_match = re.match(r"^([<>=≤≥])\s*(\d+(?:\.\d+)?)", raw_value_str)
            if comp_match:
                comp_sym = comp_match.group(1)
                comparator = comp_sym if comp_sym in ("<", ">", "<=", ">=", "=") else None
                numeric_val = float(comp_match.group(2))
            else:
                try:
                    numeric_val = float(raw_value_str)
                except ValueError:
                    numeric_val = None

            # Standardize unit
            normalized_unit = unit_validator.standardize_unit(raw_unit)

            # Map LOINC terminology
            loinc_concept = loinc_adapter.map_test_name(raw_test_name)
            loinc_code = loinc_concept.loinc_code if loinc_concept else None
            normalized_test_name = loinc_concept.canonical_display if loinc_concept else None

            # Parse reference range
            ref_range = cls._parse_reference_range(raw_ref_str)
            if not ref_range and loinc_concept and loinc_concept.reference_low is not None:
                # Use standard fallback reference only if document did not report one
                ref_range = ReferenceRange(
                    raw_text=f"{loinc_concept.reference_low} - {loinc_concept.reference_high}",
                    low=loinc_concept.reference_low,
                    high=loinc_concept.reference_high,
                    unit=loinc_concept.standard_unit,
                )

            # Evaluate derived status
            ref_low = ref_range.low if ref_range else None
            ref_high = ref_range.high if ref_range else None
            derived_status, is_abnormal = unit_validator.evaluate_derived_status(
                numeric_val, ref_low, ref_high
            )

            obs = ClinicalObservation(
                observation_id=f"obs_{uuid.uuid4().hex[:8]}",
                test_name=raw_test_name,
                original_test_name=raw_test_name,
                normalized_test_name=normalized_test_name,
                loinc_code=loinc_code,
                original_value=raw_value_str,
                numeric_value=numeric_val,
                comparator=comparator,
                original_unit=raw_unit,
                normalized_unit=normalized_unit,
                reference_range=ref_range,
                derived_status=derived_status,
                is_abnormal=is_abnormal,
                specimen=loinc_concept.specimen if loinc_concept else None,
                source_page=page_number,
                source_evidence=line_str,
                extraction_method="DETERMINISTIC_TABLE",
                confidence=0.92,
            )
            observations.append(obs)

        return observations


lab_table_extractor = LabTableExtractor()
