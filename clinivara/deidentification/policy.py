"""
De-identification transformation policies and entity configuration.
"""

from typing import Dict, Literal, Optional
from pydantic import BaseModel, Field

from clinivara.core.config import settings


class TransformationRule(BaseModel):
    """Rule defining how a detected entity category should be transformed."""
    action: Literal["redact", "tokenize", "generalize_year", "suppress"] = "redact"
    mask_label: str
    min_confidence: float = 0.60


class DeidentificationPolicy(BaseModel):
    """Configuration governing entity detection and de-identification boundaries."""

    version: str = "1.0"
    default_action: str = "redact"
    entity_rules: Dict[str, TransformationRule] = Field(
        default_factory=lambda: {
            "PERSON": TransformationRule(action="redact", mask_label="NAME", min_confidence=0.55),
            "PATIENT_ID": TransformationRule(action="redact", mask_label="PATIENT_ID", min_confidence=0.60),
            "PHONE_NUMBER": TransformationRule(action="redact", mask_label="PHONE", min_confidence=0.65),
            "EMAIL_ADDRESS": TransformationRule(action="redact", mask_label="EMAIL", min_confidence=0.70),
            "GOV_ID": TransformationRule(action="redact", mask_label="GOV_ID", min_confidence=0.65),
            "DATE_TIME": TransformationRule(action="redact", mask_label="DATE", min_confidence=0.60),
            "LOCATION": TransformationRule(action="redact", mask_label="LOCATION", min_confidence=0.60),
            "MEDICAL_LICENSE": TransformationRule(action="redact", mask_label="LICENSE", min_confidence=0.70),
            "URL": TransformationRule(action="redact", mask_label="URL", min_confidence=0.75),
            "IP_ADDRESS": TransformationRule(action="redact", mask_label="IP_ADDRESS", min_confidence=0.80),
        }
    )

    def get_rule_for_entity(self, entity_type: str) -> TransformationRule:
        return self.entity_rules.get(
            entity_type,
            TransformationRule(
                action="redact",
                mask_label=entity_type,
                min_confidence=settings.deid_confidence_threshold,
            ),
        )


default_policy = DeidentificationPolicy()
