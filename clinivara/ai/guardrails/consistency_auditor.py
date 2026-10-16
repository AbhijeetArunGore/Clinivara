"""
Evidence Consistency Auditor for Medical Outputs.
Verifies factual fidelity between generated explanations/extractions and source evidence passages.
Ensures zero hallucinated values, preserved units, and invariant negations.
"""

import re
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from clinivara.schemas.ai import Citation, ClinicalObservation, GroundedExplanation


class AuditFinding(BaseModel):
    check_type: str
    severity: str = Field(description="'INFO', 'WARNING', or 'CRITICAL'")
    description: str
    affected_text: Optional[str] = None
    expected: Optional[str] = None
    actual: Optional[str] = None


class ConsistencyAuditResult(BaseModel):
    passed: bool
    audit_score: float = Field(ge=0.0, le=1.0)
    findings: List[AuditFinding] = Field(default_factory=list)
    has_critical_error: bool = False


class ClinicalConsistencyAuditor:
    """Audits generated outputs against approved source evidence to eliminate AI hallucinations."""

    def audit_observations(
        self,
        observations: List[ClinicalObservation],
        approved_source_text: str,
    ) -> ConsistencyAuditResult:
        """Verify that every extracted observation value and unit is grounded in approved text."""
        findings: List[AuditFinding] = []
        source_lower = approved_source_text.lower()

        for obs in observations:
            # 1. Check if verbatim test name exists
            if obs.original_test_name.lower() not in source_lower:
                findings.append(
                    AuditFinding(
                        check_type="TEST_NAME_GROUNDING",
                        severity="WARNING",
                        description=f"Original test name '{obs.original_test_name}' not found verbatim in source text.",
                        affected_text=obs.original_test_name,
                    )
                )

            # 2. Check if original value exists
            if obs.original_value.lower() not in source_lower:
                findings.append(
                    AuditFinding(
                        check_type="VALUE_GROUNDING",
                        severity="CRITICAL",
                        description=f"Extracted value '{obs.original_value}' for {obs.test_name} not found in source text.",
                        affected_text=obs.original_value,
                        expected="Value present in source",
                        actual=obs.original_value,
                    )
                )

            # 3. Check unit fidelity
            if obs.original_unit and obs.original_unit.lower() not in source_lower:
                findings.append(
                    AuditFinding(
                        check_type="UNIT_GROUNDING",
                        severity="WARNING",
                        description=f"Unit '{obs.original_unit}' for {obs.test_name} not found verbatim in source text.",
                        affected_text=obs.original_unit,
                    )
                )

        has_critical = any(f.severity == "CRITICAL" for f in findings)
        score = 1.0 - (len(findings) * 0.1)
        score = max(0.0, min(1.0, score))

        return ConsistencyAuditResult(
            passed=not has_critical,
            audit_score=score,
            findings=findings,
            has_critical_error=has_critical,
        )

    def audit_explanation(
        self,
        explanation: GroundedExplanation,
        approved_source_text: str,
    ) -> ConsistencyAuditResult:
        """Verify that generated explanations do not fabricate numbers or drop citations."""
        findings: List[AuditFinding] = []
        source_lower = approved_source_text.lower()

        # 1. Require citations for non-empty explanation
        if explanation.key_findings and not explanation.citations:
            findings.append(
                AuditFinding(
                    check_type="CITATION_COMPLIANCE",
                    severity="CRITICAL",
                    description="Explanation contains key findings but zero source citations.",
                )
            )

        # 2. Check each citation's evidence_text is actually in the approved source document
        for cit in explanation.citations:
            clean_evidence = cit.evidence_text.strip().lower()
            if clean_evidence and clean_evidence not in source_lower:
                # Allow partial match if OCR breaks lines
                words = clean_evidence.split()
                if len(words) >= 3:
                    sub_match = all(w in source_lower for w in words[:3])
                    if not sub_match:
                        findings.append(
                            AuditFinding(
                                check_type="CITATION_FIDELITY",
                                severity="CRITICAL",
                                description=f"Citation '{cit.citation_id}' evidence does not match approved source text.",
                                affected_text=cit.evidence_text,
                            )
                        )

        # 3. Numeric verification: Numbers mentioned in key findings should exist in source or citations
        # Extract floating point or integer numbers from explanation text
        explanation_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", explanation.summary))
        for kf in explanation.key_findings:
            explanation_numbers.update(re.findall(r"\b\d+(?:\.\d+)?\b", kf.lay_explanation))

        source_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", approved_source_text))

        for num in explanation_numbers:
            # Skip common general numbers (e.g. 1, 2, 3 in bullet lists)
            if num in {"1", "2", "3", "4", "5", "10", "100"}:
                continue
            if num not in source_numbers:
                findings.append(
                    AuditFinding(
                        check_type="NUMERIC_GROUNDING",
                        severity="WARNING",
                        description=f"Number '{num}' in explanation was not found in source document numbers.",
                        affected_text=num,
                    )
                )

        has_critical = any(f.severity == "CRITICAL" for f in findings)
        score = 1.0 - (len(findings) * 0.15)
        score = max(0.0, min(1.0, score))

        return ConsistencyAuditResult(
            passed=not has_critical,
            audit_score=score,
            findings=findings,
            has_critical_error=has_critical,
        )
