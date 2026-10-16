"""
Clinical fact extraction orchestrator.
Extracts observations, diagnoses, symptoms, and medications with negation and temporality.
"""

import re
from typing import List, Tuple
from clinivara.clinical.document_classifier import document_classifier
from clinivara.clinical.table_extractor import lab_table_extractor
from clinivara.nlp.negation import clinical_negation_detector
from clinivara.nlp.preprocessing import clinical_preprocessor
from clinivara.nlp.section_detection import section_detector
from clinivara.schemas.ai import (
    ClinicalEntity,
    ExtractedClinicalData,
    MedicationEntity,
)

# Known clinical terms for entity parsing
KNOWN_DIAGNOSES = [
    r"Type 2 Diabetes(?: Mellitus)?",
    r"Hypertension",
    r"Chronic Kidney Disease",
    r"Dyslipidemia",
    r"Essential Hypertension",
    r"Acute Coronary Syndrome",
    r"GERD",
    r"Asthma",
    r"Pneumonia",
    r"Anemia",
    r"मधुमेह",
    r"उच्च रक्तदाब",
    r"उच्च रक्तचाप",
]

KNOWN_SYMPTOMS = [
    r"fatigue",
    r"blurred vision",
    r"chest pain",
    r"shortness of breath",
    r"headache",
    r"fever",
    r"cough",
    r"थकवा",
    r"धूसर दृष्टी",
    r"छातीत दुखणे",
    r"थकान",
    r"सीने में दर्द",
]

MEDICATION_REGEX = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(\d+(?:\.\d+)?\s*(?:mg|g|mcg|ml))\s*(PO|IV|SC)?\s*(BID|TID|QID|daily|HS|PRN)?\b",
    re.IGNORECASE,
)


class ClinicalExtractor:
    """Orchestrates structured clinical extraction across observations and entities."""

    def extract(
        self,
        document_id: str,
        tenant_id: str,
        approved_text: str,
        page_count: int = 1,
    ) -> ExtractedClinicalData:
        return self.extract_clinical_data(document_id=document_id, tenant_id=tenant_id, text=approved_text)

    def extract_clinical_data(
        self,
        document_id: str,
        tenant_id: str,
        text: str,
    ) -> ExtractedClinicalData:
        # 1. Document classification
        classification = document_classifier.classify(text)

        # 2. Section detection
        sections = section_detector.detect_sections(text)

        # 3. Extract laboratory observations
        observations = lab_table_extractor.extract_observations(text)

        # 4. Extract clinical entities with negation and temporality
        sentences = clinical_preprocessor.split_sentences(text)
        entities: List[ClinicalEntity] = []
        medications: List[MedicationEntity] = []

        for sent in sentences:
            is_neg, is_unc, temp, trigger = clinical_negation_detector.analyze_assertion(sent)

            # Check diagnoses
            for diag_pat in KNOWN_DIAGNOSES:
                match = re.search(diag_pat, sent, re.IGNORECASE)
                if match:
                    entities.append(
                        ClinicalEntity(
                            text=match.group(0),
                            entity_type="DIAGNOSIS",
                            is_negated=is_neg,
                            is_uncertain=is_unc,
                            temporality=temp,
                            source_evidence=sent,
                            source_page=1,
                        )
                    )

            # Check symptoms
            for sym_pat in KNOWN_SYMPTOMS:
                match = re.search(sym_pat, sent, re.IGNORECASE)
                if match:
                    entities.append(
                        ClinicalEntity(
                            text=match.group(0),
                            entity_type="SYMPTOM",
                            is_negated=is_neg,
                            is_uncertain=is_unc,
                            temporality=temp,
                            source_evidence=sent,
                            source_page=1,
                        )
                    )

            # Check medications
            med_match = MEDICATION_REGEX.search(sent)
            if med_match:
                med_name = med_match.group(1).strip()
                med_dose = med_match.group(2).strip()
                med_route = med_match.group(3).strip() if med_match.group(3) else None
                med_freq = med_match.group(4).strip() if med_match.group(4) else None

                # Exclude false positives that are lab tests
                if med_name.lower() not in ("fasting glucose", "blood pressure", "hba1c"):
                    medications.append(
                        MedicationEntity(
                            name=med_name,
                            dosage=med_dose,
                            route=med_route,
                            frequency=med_freq,
                            is_active=not is_neg,
                            source_evidence=sent,
                            source_page=1,
                        )
                    )

        # 5. Compute extraction quality and review flags
        review_required = False
        review_reasons = []

        if len(observations) == 0 and len(entities) == 0:
            review_required = True
            review_reasons.append("No structured clinical observations or entities were extracted.")

        quality_score = 0.95 if observations else (0.80 if entities else 0.50)

        return ExtractedClinicalData(
            schema_version="1.0",
            document_id=document_id,
            tenant_id=tenant_id,
            classification=classification,
            observations=observations,
            entities=entities,
            medications=medications,
            extraction_quality_score=quality_score,
            review_required=review_required,
            review_reasons=review_reasons,
        )


clinical_extractor = ClinicalExtractor()
