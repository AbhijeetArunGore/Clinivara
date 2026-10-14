"""
Multi-layer clinical de-identification engine.

Combines:
1. Microsoft Presidio Analyzer with spaCy NLP.
2. Custom recognizers for MRNs, Indian healthcare identifiers (Aadhaar, PAN, ABHA), and doctor prefixes.
3. Deterministic pattern recognizers for guaranteed boundary detection.
4. Clinical whitelist protection to prevent corrupting medical terminology (diagnoses, lab tests, medications).
5. Configurable transformations (redaction, generalization, salted tokenization).
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from clinivara.audit.audit_logger import audit_logger
from clinivara.core.config import settings
from clinivara.deidentification.policy import DeidentificationPolicy, default_policy
from clinivara.deidentification.recognizers.custom_recognizers import build_custom_presidio_recognizers
from clinivara.deidentification.recognizers.patterns import (
    AADHAAR_REGEX,
    ABHA_NUMBER_REGEX,
    DOCTOR_NAME_PREFIX_REGEX,
    HOSPITAL_MRN_REGEX,
    INDIAN_PHONE_REGEX,
    PAN_REGEX,
)
from clinivara.deidentification.token_vault import token_vault

# Protected clinical vocabulary that must NEVER be redacted as identifiers
PROTECTED_CLINICAL_TERMS: Set[str] = {
    "diabetes", "type 2 diabetes", "hypertension", "asthma", "pneumonia",
    "covid-19", "anemia", "tuberculosis", "chronic kidney disease",
    "hba1c", "glucose", "creatinine", "hemoglobin", "wbc", "rbc", "platelet",
    "sodium", "potassium", "bilirubin", "ast", "alt", "urea", "bun",
    "metformin", "lisinopril", "aspirin", "atorvastatin", "amlodipine",
    "insulin", "amoxicillin", "paracetamol", "ibuprofen", "omeprazole",
    "negative", "positive", "normal", "abnormal", "elevated", "borderline",
    "mg/dl", "mmol/l", "g/dl", "miu/l", "meq/l", "cells/mcl", "%", "mmhg",
    "outpatient clinic note", "outpatient clinic", "clinic note", "discharge summary",
    "emergency department", "hospital", "clinic", "department",
    "hs", "po", "bid", "tid", "qid", "prn", "stat", "pan", "mrn", "uhid", "abha", "pid", "hsp", "dob", "bp",
}


class DeidentifiedSpan:
    """Represents a detected sensitive span."""

    def __init__(self, start: int, end: int, entity_type: str, score: float, text: str):
        self.start = start
        self.end = end
        self.entity_type = entity_type
        self.score = score
        self.text = text


class DeidentificationEngine:
    """Multi-layer sensitive entity detection and de-identification engine."""

    def __init__(self, policy: Optional[DeidentificationPolicy] = None):
        self.policy = policy or default_policy
        self._analyzer = None
        self._init_presidio()

    def _init_presidio(self) -> None:
        """Initialize Presidio Analyzer with robust Spacy NLP engine and custom recognizers."""
        try:
            import spacy
            from presidio_analyzer import AnalyzerEngine
            from presidio_analyzer.nlp_engine import SpacyNlpEngine

            try:
                nlp = spacy.load("en_core_web_sm")
            except Exception:
                nlp = spacy.blank("en")

            engine = SpacyNlpEngine(models={"en": "en"})
            engine.nlp = {"en": nlp}

            self._analyzer = AnalyzerEngine(nlp_engine=engine)
            for rec in build_custom_presidio_recognizers():
                self._analyzer.registry.add_recognizer(rec)
        except Exception:
            # Engine falls back gracefully to deterministic multi-pattern scanner.
            self._analyzer = None

    def _detect_pattern_spans(self, text: str) -> List[DeidentifiedSpan]:
        """Deterministic pattern matching for high-confidence structured identifiers."""
        spans: List[DeidentifiedSpan] = []

        patterns = [
            (re.compile(HOSPITAL_MRN_REGEX, re.IGNORECASE), "PATIENT_ID", 0.98),
            (re.compile(AADHAAR_REGEX), "GOV_ID", 0.95),
            (re.compile(PAN_REGEX), "GOV_ID", 0.98),
            (re.compile(ABHA_NUMBER_REGEX), "PATIENT_ID", 0.98),
            (re.compile(INDIAN_PHONE_REGEX), "PHONE_NUMBER", 0.95),
            (re.compile(DOCTOR_NAME_PREFIX_REGEX, re.IGNORECASE), "PERSON", 0.92),
            (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "EMAIL_ADDRESS", 0.98),
            # Explicit dates (e.g. 12/04/1985, 2024-05-19, 15-Aug-1990)
            (re.compile(r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b"), "DATE_TIME", 0.90),
            (re.compile(r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]+\d{2,4}\b", re.IGNORECASE), "DATE_TIME", 0.90),
            (re.compile(r"\b\d{1,2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*-\d{2,4}\b", re.IGNORECASE), "DATE_TIME", 0.90),
            # Patient Name prefix (e.g. Patient: John Doe, Pt Name: Sunita Rao)
            (re.compile(r"\b(?:Patient(?:\s+Name)?|Pt(?:\s+Name)?)[ \t]*:[ \t]*([A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+){1,3})\b", re.IGNORECASE), "PERSON", 0.95),
        ]

        for regex, entity_type, score in patterns:
            for match in regex.finditer(text):
                # If group 1 matched (e.g. inside prefix), capture that span
                if match.lastindex and match.lastindex >= 1 and entity_type == "PERSON":
                    start = match.start(1)
                    end = match.end(1)
                    matched_str = match.group(1).strip()
                else:
                    start = match.start()
                    end = match.end()
                    matched_str = match.group(0).strip()

                # Check against protected medical terms
                if matched_str.lower() in PROTECTED_CLINICAL_TERMS:
                    continue
                spans.append(
                    DeidentifiedSpan(
                        start=start,
                        end=end,
                        entity_type=entity_type,
                        score=score,
                        text=matched_str,
                    )
                )

        return spans

    def _detect_presidio_spans(self, text: str) -> List[DeidentifiedSpan]:
        """Detect entities using Presidio Analyzer if initialized."""
        if not self._analyzer:
            return []

        spans: List[DeidentifiedSpan] = []
        try:
            results = self._analyzer.analyze(
                text=text,
                language="en",
                score_threshold=settings.deid_confidence_threshold,
            )
            for res in results:
                # Discard generic ORGANIZATION or NRP tags on clinical abbreviations or headings
                if res.entity_type in ("ORGANIZATION", "NRP"):
                    continue

                raw_slice = text[res.start:res.end]
                # Filter out protected clinical terms
                if raw_slice.lower() in PROTECTED_CLINICAL_TERMS:
                    continue
                spans.append(
                    DeidentifiedSpan(
                        start=res.start,
                        end=res.end,
                        entity_type=res.entity_type,
                        score=res.score,
                        text=raw_slice,
                    )
                )
        except Exception:
            pass

        return spans

    def deidentify(
        self,
        text: str,
        tenant_id: str,
        document_id: str,
        correlation_id: str,
    ) -> Tuple[str, Dict[str, int], List[Dict[str, Any]]]:
        """
        Detect sensitive entities and apply configured transformation policies.
        Returns:
            (sanitized_text, transformed_counts, safe_entity_summary)
        """
        # 1. Gather candidate spans from both Presidio and pattern recognizers
        candidates: List[DeidentifiedSpan] = []
        candidates.extend(self._detect_pattern_spans(text))
        candidates.extend(self._detect_presidio_spans(text))

        # 2. Filter by policy threshold
        filtered: List[DeidentifiedSpan] = []
        for span in candidates:
            rule = self.policy.get_rule_for_entity(span.entity_type)
            if span.score >= rule.min_confidence:
                filtered.append(span)

        # 3. Resolve overlaps: highest confidence/specific score wins
        filtered.sort(key=lambda s: (-s.score, -(s.end - s.start), s.start))
        selected: List[DeidentifiedSpan] = []
        for s in filtered:
            if not any(max(s.start, sel.start) < min(s.end, sel.end) for sel in selected):
                selected.append(s)

        # Sort selected by start ascending for deterministic application
        selected.sort(key=lambda s: s.start)

        # 4. Apply transformations in reverse order to preserve string offsets
        transformed_counts: Dict[str, int] = {}
        safe_entity_summary: List[Dict[str, Any]] = []

        chars = list(text)
        for span in reversed(selected):
            rule = self.policy.get_rule_for_entity(span.entity_type)

            # Determine replacement string
            if rule.action == "tokenize" and settings.enable_longitudinal_tokens:
                replacement = token_vault.resolve_token(
                    tenant_id=tenant_id,
                    document_id=document_id,
                    entity_type=rule.mask_label,
                    raw_value=span.text,
                )
            elif rule.action == "generalize_year" and span.entity_type == "DATE_TIME":
                year_match = re.search(r"\b(19\d{2}|20\d{2})\b", span.text)
                if year_match:
                    replacement = f"[DATE_YEAR_{year_match.group(1)}]"
                else:
                    replacement = f"[{rule.mask_label}]"
            elif rule.action == "suppress":
                replacement = ""
            else:
                # Default irreversible redaction: [NAME], [PATIENT_ID], etc.
                replacement = f"[{rule.mask_label}]"

            # Apply replacement
            chars[span.start:span.end] = list(replacement)

            # Record safe aggregate statistics (never logging raw text)
            transformed_counts[rule.mask_label] = transformed_counts.get(rule.mask_label, 0) + 1
            safe_entity_summary.append({
                "entity_type": span.entity_type,
                "mask_label": rule.mask_label,
                "confidence_score": round(span.score, 2),
                "span_length": span.end - span.start,
            })

        sanitized_text = "".join(chars)

        # Audit event
        audit_logger.record_event(
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            event_type="DEIDENTIFICATION_COMPLETED",
            status="SUCCESS",
            document_id=document_id,
            details={
                "policy_version": self.policy.version,
                "entities_transformed_count": sum(transformed_counts.values()),
                "entity_types": list(transformed_counts.keys()),
            },
        )

        return sanitized_text, transformed_counts, safe_entity_summary


deidentification_engine = DeidentificationEngine()
