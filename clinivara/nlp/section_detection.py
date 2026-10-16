"""
Multilingual clinical section detection supporting English, Hindi, and Marathi medical documents.
"""

import re
from typing import List
from pydantic import BaseModel, ConfigDict, Field


class DetectedSection(BaseModel):
    """Normalized clinical section with language and boundary tracking."""
    model_config = ConfigDict(frozen=True)

    title: str = Field(description="Canonical section identifier")
    original_heading: str = Field(description="Verbatim heading string from source")
    content: str = Field(description="Body content of the section")
    start_char: int
    end_char: int

    @property
    def section_type(self) -> str:
        return self.title


SECTION_HEADING_PATTERNS = [
    # Chief Complaint
    (r"(?:CHIEF\s+COMPLAINT|REASON\s+FOR\s+VISIT|मुख्य\s+समस्या|मुख्य\s+तक्रार)", "CHIEF_COMPLAINT"),
    # History
    (r"(?:HISTORY\s+OF\s+PRESENT\s+ILLNESS|HPI|PAST\s+MEDICAL\s+HISTORY|PMH|MEDICAL\s+HISTORY|पूर्व\s+इतिहास|मागील\s+इतिहास|इतिहास)", "HISTORY"),
    # Medications
    (r"(?:CURRENT\s+MEDICATIONS?|MEDICATIONS?|RX|दवाएं|औषधे|सध्याची\s+औषधे)", "MEDICATIONS"),
    # Investigations / Labs
    (r"(?:LABORATORY(?:\s+DATA|\s+RESULTS)?|INVESTIGATIONS|LABS|जांच\s+परिणाम|प्रयोगशाळा\s+तपासणी|चाचण्या|तपासणी\s+अहवाल)", "LABORATORY_RESULTS"),
    # Diagnoses / Impression
    (r"(?:DIAGNOSIS|DIAGNOSES|IMPRESSION|ASSESSMENT|निदान|रोगनिदान)", "DIAGNOSIS"),
    # Plan / Advice
    (r"(?:PLAN|RECOMMENDATIONS|FOLLOW\s*UP|सल्ला|योजना|पुढील\s+उपचार)", "PLAN"),
    # Discharge Summary
    (r"(?:DISCHARGE\s+SUMMARY|HOSPITAL\s+COURSE|डिस्चार्ज\s+सारांश)", "DISCHARGE_SUMMARY"),
]

COMPILED_SECTION_REGEX = re.compile(
    r"^[\s\*\#\-]*(" + "|".join(pat for pat, _ in SECTION_HEADING_PATTERNS) + r")\s*[:\-\n]",
    re.IGNORECASE | re.MULTILINE,
)


class SectionDetector:
    """Detects and parses clinical sections across English, Hindi, and Marathi documents."""

    @staticmethod
    def detect_sections(text: str) -> List[DetectedSection]:
        if not text or not text.strip():
            return []

        matches = list(COMPILED_SECTION_REGEX.finditer(text))
        if not matches:
            return [
                DetectedSection(
                    title="GENERAL_REPORT",
                    original_heading="GENERAL_REPORT",
                    content=text.strip(),
                    start_char=0,
                    end_char=len(text),
                )
            ]

        sections: List[DetectedSection] = []

        # Preamble before first header
        if matches[0].start() > 0:
            preamble_text = text[:matches[0].start()].strip()
            if preamble_text:
                sections.append(
                    DetectedSection(
                        title="PREAMBLE",
                        original_heading="PREAMBLE",
                        content=preamble_text,
                        start_char=0,
                        end_char=matches[0].start(),
                    )
                )

        for i, match in enumerate(matches):
            raw_heading = match.group(1).strip()
            start_pos = match.end()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start_pos:end_pos].strip()

            # Map raw heading to canonical title
            canonical_title = "GENERAL"
            for pat, title in SECTION_HEADING_PATTERNS:
                if re.match(pat, raw_heading, re.IGNORECASE):
                    canonical_title = title
                    break

            sections.append(
                DetectedSection(
                    title=canonical_title,
                    original_heading=raw_heading,
                    content=content,
                    start_char=match.start(),
                    end_char=end_pos,
                )
            )

        return sections

    @classmethod
    def segment_sections(cls, text: str) -> List[DetectedSection]:
        return cls.detect_sections(text)


ClinicalSectionDetector = SectionDetector
section_detector = SectionDetector()
