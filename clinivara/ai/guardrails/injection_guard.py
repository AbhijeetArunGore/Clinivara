"""
Prompt Injection and Jailbreak Guardrail for Medical Documents and Queries.
Protects AI prompts and inference pipelines against adversarial instruction injection.
"""

import re
from typing import List, Tuple


class PromptInjectionGuard:
    """Detects and sanitizes prompt injection patterns in untrusted medical documents and user inputs."""

    # English, Hindi, and Marathi prompt injection patterns
    INJECTION_PATTERNS = [
        # English jailbreaks / system override attempts
        r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
        r"disregard\s+(all\s+)?(previous|prior|system)\s+instructions",
        r"forget\s+(all\s+)?previous\s+instructions",
        r"you\s+are\s+now\s+an?\s+(unrestricted|jailbroken|new)\s+assistant",
        r"system\s*:\s*you\s+are",
        r"new\s+system\s+prompt",
        r"reveal\s+(your\s+)?(secret|internal|system)\s+(prompt|instructions)",
        r"print\s+system\s+prompt",
        r"override\s+safety\s+guidelines",
        r"act\s+as\s+dan",
        r"developer\s+mode\s+enabled",
        r"output\s+the\s+preceding\s+text",
        
        # Hindi jailbreak attempts
        r"पिछले\s+(सभी\s+)?निर्देशों\s+को\s+(भूल\s+जाएं|अनदेखा\s+करें|रद्द\s+करें)",
        r"सिस्टम\s+प्रॉम्प्ट\s+दिखाएं",
        r"नए\s+निर्देश\s+का\s+पालन\s+करें",
        r"सुरक्षा\s+नियम\s+तोड़ें",

        # Marathi jailbreak attempts
        r"मागील\s+(सर्व\s+)?सूचना\s+(दुर्लक्षित\s+करा|विसरा|रद्द\s+करा)",
        r"सिस्टम\s+प्रॉम्प्ट\s+दाखवा",
        r"सुरक्षा\s+नियम\s+मोडा",
    ]

    def __init__(self):
        self._compiled_regexes = [
            re.compile(pattern, re.IGNORECASE | re.UNICODE) for pattern in self.INJECTION_PATTERNS
        ]

    def inspect_text(self, text: str) -> Tuple[bool, List[str]]:
        """
        Scan text for prompt injection signatures.
        Returns:
            Tuple[is_safe: bool, matched_patterns: List[str]]
        """
        if not text:
            return True, []

        matches = []
        for regex in self._compiled_regexes:
            found = regex.findall(text)
            if found:
                matches.append(regex.pattern)

        is_safe = len(matches) == 0
        return is_safe, matches

    def sanitize_delimiters(self, text: str) -> str:
        """
        Sanitize XML/tag delimiters to prevent tag breaking attacks.
        E.g. transforms literal </document_data> or </evidence> tags in input into harmless escaped forms.
        """
        if not text:
            return ""
        sanitized = text.replace("</document_data>", "[REDACTED_DELIMITER]")
        sanitized = sanitized.replace("<document_data>", "[REDACTED_DELIMITER]")
        sanitized = sanitized.replace("</evidence>", "[REDACTED_DELIMITER]")
        sanitized = sanitized.replace("<evidence>", "[REDACTED_DELIMITER]")
        sanitized = sanitized.replace("</candidate_data>", "[REDACTED_DELIMITER]")
        sanitized = sanitized.replace("<candidate_data>", "[REDACTED_DELIMITER]")
        sanitized = sanitized.replace("</validated_facts>", "[REDACTED_DELIMITER]")
        sanitized = sanitized.replace("<validated_facts>", "[REDACTED_DELIMITER]")
        return sanitized
