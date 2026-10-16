"""
Multilingual document intelligence, language registry, detection, and translation.
"""

from clinivara.multilingual.language_detection import language_detector
from clinivara.multilingual.language_registry import language_registry
from clinivara.multilingual.terminology import clinical_terminology
from clinivara.multilingual.translation import clinical_translator
from clinivara.multilingual.unicode_normalizer import devanagari_normalizer

__all__ = [
    "language_registry",
    "language_detector",
    "devanagari_normalizer",
    "clinical_terminology",
    "clinical_translator",
]
