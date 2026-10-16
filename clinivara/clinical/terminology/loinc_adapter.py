"""
Baseline LOINC clinical laboratory terminology mapping adapter.
"""

from typing import Dict, Optional
from pydantic import BaseModel, ConfigDict


class LOINCConcept(BaseModel):
    """Canonical LOINC observation definition."""
    model_config = ConfigDict(frozen=True)

    loinc_code: str
    canonical_display: str
    standard_unit: str
    specimen: str
    reference_low: Optional[float] = None
    reference_high: Optional[float] = None


LOINC_DICTIONARY: Dict[str, LOINCConcept] = {
    "hba1c": LOINCConcept(
        loinc_code="4548-4",
        canonical_display="Hemoglobin A1c/Hemoglobin.total in Blood",
        standard_unit="%",
        specimen="Whole Blood",
        reference_low=4.0,
        reference_high=5.6,
    ),
    "glycated hemoglobin": LOINCConcept(
        loinc_code="4548-4",
        canonical_display="Hemoglobin A1c/Hemoglobin.total in Blood",
        standard_unit="%",
        specimen="Whole Blood",
        reference_low=4.0,
        reference_high=5.6,
    ),
    "fasting blood glucose": LOINCConcept(
        loinc_code="1558-6",
        canonical_display="Fasting Glucose [Mass/volume] in Blood",
        standard_unit="mg/dL",
        specimen="Blood",
        reference_low=70.0,
        reference_high=99.0,
    ),
    "fasting blood sugar": LOINCConcept(
        loinc_code="1558-6",
        canonical_display="Fasting Glucose [Mass/volume] in Blood",
        standard_unit="mg/dL",
        specimen="Blood",
        reference_low=70.0,
        reference_high=99.0,
    ),
    "fasting glucose": LOINCConcept(
        loinc_code="1558-6",
        canonical_display="Fasting Glucose [Mass/volume] in Blood",
        standard_unit="mg/dL",
        specimen="Blood",
        reference_low=70.0,
        reference_high=99.0,
    ),
    "glucose": LOINCConcept(
        loinc_code="2345-7",
        canonical_display="Glucose [Mass/volume] in Serum or Plasma",
        standard_unit="mg/dL",
        specimen="Serum",
        reference_low=70.0,
        reference_high=140.0,
    ),
    "creatinine": LOINCConcept(
        loinc_code="2160-0",
        canonical_display="Creatinine [Mass/volume] in Serum or Plasma",
        standard_unit="mg/dL",
        specimen="Serum",
        reference_low=0.7,
        reference_high=1.3,
    ),
    "serum creatinine": LOINCConcept(
        loinc_code="2160-0",
        canonical_display="Creatinine [Mass/volume] in Serum or Plasma",
        standard_unit="mg/dL",
        specimen="Serum",
        reference_low=0.7,
        reference_high=1.3,
    ),
    "hemoglobin": LOINCConcept(
        loinc_code="718-7",
        canonical_display="Hemoglobin [Mass/volume] in Blood",
        standard_unit="g/dL",
        specimen="Blood",
        reference_low=13.5,
        reference_high=17.5,
    ),
    "हीमोग्लोबिन": LOINCConcept(
        loinc_code="718-7",
        canonical_display="Hemoglobin [Mass/volume] in Blood",
        standard_unit="g/dL",
        specimen="Blood",
        reference_low=13.5,
        reference_high=17.5,
    ),
    "हिमोग्लोबिन": LOINCConcept(
        loinc_code="718-7",
        canonical_display="Hemoglobin [Mass/volume] in Blood",
        standard_unit="g/dL",
        specimen="Blood",
        reference_low=13.5,
        reference_high=17.5,
    ),
    "platelet count": LOINCConcept(
        loinc_code="777-3",
        canonical_display="Platelets [#/volume] in Blood",
        standard_unit="cells/mcL",
        specimen="Blood",
        reference_low=150000.0,
        reference_high=450000.0,
    ),
    "total cholesterol": LOINCConcept(
        loinc_code="2093-3",
        canonical_display="Cholesterol [Mass/volume] in Serum or Plasma",
        standard_unit="mg/dL",
        specimen="Serum",
        reference_low=125.0,
        reference_high=200.0,
    ),
    "triglycerides": LOINCConcept(
        loinc_code="2571-8",
        canonical_display="Triglyceride [Mass/volume] in Serum or Plasma",
        standard_unit="mg/dL",
        specimen="Serum",
        reference_low=50.0,
        reference_high=150.0,
    ),
    "potassium": LOINCConcept(
        loinc_code="2823-3",
        canonical_display="Potassium [Moles/volume] in Serum or Plasma",
        standard_unit="mmol/L",
        specimen="Serum",
        reference_low=3.5,
        reference_high=5.0,
    ),
    "sodium": LOINCConcept(
        loinc_code="2951-2",
        canonical_display="Sodium [Moles/volume] in Serum or Plasma",
        standard_unit="mmol/L",
        specimen="Serum",
        reference_low=135.0,
        reference_high=145.0,
    ),
    "tsh": LOINCConcept(
        loinc_code="3016-3",
        canonical_display="Thyrotropin [Units/volume] in Serum or Plasma",
        standard_unit="mIU/L",
        specimen="Serum",
        reference_low=0.4,
        reference_high=4.0,
    ),
}


class LOINCTerminologyAdapter:
    """Terminology mapping adapter for laboratory tests."""

    @staticmethod
    def map_test_name(raw_name: str) -> Optional[LOINCConcept]:
        if not raw_name:
            return None
        cleaned = raw_name.lower().strip()
        # Direct lookup
        if cleaned in LOINC_DICTIONARY:
            return LOINC_DICTIONARY[cleaned]

        # Substring lookup
        for key, concept in LOINC_DICTIONARY.items():
            if key in cleaned:
                return concept

        return None


LOINCAdapter = LOINCTerminologyAdapter
loinc_adapter = LOINCTerminologyAdapter()
