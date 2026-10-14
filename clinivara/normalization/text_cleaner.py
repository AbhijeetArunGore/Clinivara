"""
Conservative clinical text cleaner and section organizer.

Enforces:
1. Unicode normalization (NFKC) while preserving scientific/clinical symbols (μ, <, >, ≤, ≥, ±, %, °, -).
2. Safe whitespace and line ending normalization without destroying tabular layouts.
3. Strict preservation of dosages, units, and laboratory values.
4. Parsing into structured clinical sections based on standard clinical headers.
"""

import re
import unicodedata
from typing import List, Tuple
from clinivara.schemas.approved_output import ClinicalSection

# Standard clinical section headings recognized in clinical reports
CLINICAL_SECTION_PATTERNS = [
    r"(?:CHIEF\s+COMPLAINT|REASON\s+FOR\s+VISIT)",
    r"(?:HISTORY\s+OF\s+PRESENT\s+ILLNESS|HPI)",
    r"(?:PAST\s+MEDICAL\s+HISTORY|PMH)",
    r"(?:PAST\s+SURGICAL\s+HISTORY|PSH)",
    r"(?:MEDICATIONS?|CURRENT\s+MEDICATIONS?)",
    r"(?:ALLERGIES(?:\s+AND\s+ADVERSE\s+REACTIONS)?)",
    r"(?:PHYSICAL\s+EXAMINATION|PE)",
    r"(?:LABORATORY(?:\s+DATA|\s+RESULTS)?|INVESTIGATIONS|LABS)",
    r"(?:DIAGNOSIS|DIAGNOSES|IMPRESSION|ASSESSMENT)",
    r"(?:PLAN|TREATMENT\s+PLAN|RECOMMENDATIONS)",
    r"(?:DISCHARGE\s+SUMMARY|HOSPITAL\s+COURSE)",
]

SECTION_REGEX = re.compile(
    r"^[\s\*\#\-]*(" + "|".join(CLINICAL_SECTION_PATTERNS) + r")\s*[:\-\n]",
    re.IGNORECASE | re.MULTILINE,
)


class TextCleaner:
    """Conservative clinical text cleaner."""

    @staticmethod
    def clean_text(text: str) -> str:
        """
        Safely normalizes text without altering clinical meaning or measurements.
        """
        if not text:
            return ""

        # 1. Unicode normalization (NFKC ensures ligature separation without corrupting micro/mu)
        normalized = unicodedata.normalize("NFKC", text)

        # 2. Standardize line endings (\r\n -> \n)
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")

        # 3. Strip non-printable / control characters (preserve tab and newline)
        # Specifically strip form-feed (\x0c) often introduced by PDF extractors
        cleaned_chars = []
        for ch in normalized:
            code = ord(ch)
            if ch in ("\n", "\t"):
                cleaned_chars.append(ch)
            elif code < 32 or (127 <= code <= 159):
                cleaned_chars.append(" ")
            elif ch == "\ufffd":  # Unicode replacement character
                cleaned_chars.append(" ")
            else:
                cleaned_chars.append(ch)
        normalized = "".join(cleaned_chars)

        # 4. Collapse excessive blank lines (> 2 into 2) to preserve readability
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)

        # 5. Strip trailing horizontal whitespace on each line
        lines = [line.rstrip() for line in normalized.split("\n")]
        return "\n".join(lines).strip()

    @staticmethod
    def extract_sections(text: str) -> List[ClinicalSection]:
        """
        Extract recognizable clinical sections while keeping unsectioned content intact.
        """
        matches = list(SECTION_REGEX.finditer(text))
        if not matches:
            return [ClinicalSection(title="GENERAL_REPORT", content=text.strip())]

        sections: List[ClinicalSection] = []

        # If there is introductory text before the first heading
        first_start = matches[0].start()
        if first_start > 0:
            preamble = text[:first_start].strip()
            if preamble:
                sections.append(ClinicalSection(title="PREAMBLE", content=preamble))

        for i, match in enumerate(matches):
            raw_title = match.group(1).upper()
            start_pos = match.end()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section_content = text[start_pos:end_pos].strip()

            sections.append(
                ClinicalSection(
                    title=raw_title,
                    content=section_content,
                )
            )

        return sections


text_cleaner = TextCleaner()
