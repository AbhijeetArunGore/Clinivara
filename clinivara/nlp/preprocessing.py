"""
Multilingual clinical text preprocessing and sentence segmentation.
"""

import re
from typing import List


class ClinicalPreprocessor:
    """Preprocesses multilingual clinical text into coherent sentences and semantic tokens."""

    @staticmethod
    def split_sentences(text: str) -> List[str]:
        """
        Splits text into sentences supporting both Latin (. ? !) and Devanagari (। ॥ .) terminators.
        Preserves decimal numbers like '8.4%' without splitting.
        """
        if not text:
            return []

        # Replace Devanagari danda with periods
        normalized = text.replace("\u0964", ".").replace("\u0965", ".")

        # Split on sentence boundaries: period/question mark/exclamation followed by space or newline,
        # but not when surrounded by digits (e.g. 8.4)
        sentence_regex = re.compile(r"(?<!\d)[.?!]+(?!\d)\s+|\n\n+")
        raw_sentences = sentence_regex.split(normalized)

        clean_sentences = []
        for s in raw_sentences:
            s_clean = s.strip()
            if s_clean:
                clean_sentences.append(s_clean)

        return clean_sentences

    @classmethod
    def segment_sentences(cls, text: str) -> List[str]:
        return cls.split_sentences(text)


MultilingualClinicalPreprocessor = ClinicalPreprocessor
clinical_preprocessor = ClinicalPreprocessor()
