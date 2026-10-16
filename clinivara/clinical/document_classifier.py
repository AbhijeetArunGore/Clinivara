"""
Clinical document classifier supporting hematology, biochemistry, discharge summaries, and notes.
"""

import re
from typing import Dict, List, Tuple
from clinivara.multilingual.language_detection import language_detector
from clinivara.schemas.ai import DocumentClassificationResult

CATEGORY_SIGNATURES: Dict[str, List[str]] = {
    "DIABETES_PANEL": ["hba1c", "glycated hemoglobin", "fasting glucose", "postprandial", "रक्त शर्करा", "डायबिटीज"],
    "HEMATOLOGY_CBC": ["cbc", "complete blood count", "hemoglobin", "wbc", "rbc", "platelet", "mcv", "हिमोग्लोबिन", "हीमोग्लोबिन", "रक्तपेशी", "रक्त गणना", "सीबीसी"],
    "LIPID_PROFILE": ["lipid profile", "cholesterol", "triglycerides", "hdl", "ldl", "vldl", "कोलेस्ट्रॉल", "चरबी"],
    "KIDNEY_FUNCTION": ["kft", "rft", "renal function", "creatinine", "blood urea", "bun", "uric acid", "किडनी", "मूत्रपिंड"],
    "LIVER_FUNCTION": ["lft", "liver function", "bilirubin", "sgot", "sgpt", "alt", "ast", "alkaline phosphatase", "यकृत"],
    "THYROID_PANEL": ["tsh", "thyroid", "free t3", "free t4", "थायराइड"],
    "BIOCHEMISTRY_METABOLIC": [
        "biochemistry", "biochemistry examination", "serum electrolytes", "glucose",
        "बायोकेमिस्ट्री", "रक्तातील साखर", "साखर", "ग्लूकोज", "युरिया", "वैद्यकीय चाचणी अहवाल - बायोकेमिस्ट्री"
    ],
    "DISCHARGE_SUMMARY": ["discharge summary", "hospital discharge", "hospital course", "admission date", "डिस्चार्ज सारांश"],
    "PRESCRIPTION": ["prescription", "rx", "dosage", "tablet", "capsule", "दवाएं", "औषधे"],
    "CLINICAL_NOTE": ["outpatient clinic note", "progress note", "clinic visit", "chief complaint", "रुग्ण तपासणी"],
}


class ClinicalDocumentClassifier:
    """Classifies clinical reports and identifies primary/secondary languages and evidence."""

    @staticmethod
    def classify(text: str) -> DocumentClassificationResult:
        if not text or not text.strip():
            return DocumentClassificationResult(
                category="UNKNOWN",
                confidence=0.0,
                detected_language="unknown",
                secondary_languages=[],
                is_multilingual=False,
                warnings=["Document text was empty."],
            )

        # 1. Detect language
        lang_res = language_detector.detect_language(text)

        # 2. Score categories based on keyword frequency and title prominence
        lower_text = text.lower()
        first_page_text = lower_text[:1500]  # Headers usually carry high classification signal

        scores: Dict[str, float] = {}
        evidence_spans: Dict[str, List[str]] = {}

        for category, keywords in CATEGORY_SIGNATURES.items():
            matched_keywords = []
            score = 0.0

            for kw in keywords:
                # Higher weight if keyword appears in header
                if kw in first_page_text:
                    score += 2.0
                    matched_keywords.append(kw)
                elif kw in lower_text:
                    score += 1.0
                    matched_keywords.append(kw)

            if score > 0:
                scores[category] = score
                evidence_spans[category] = matched_keywords

        if not scores:
            return DocumentClassificationResult(
                category="UNKNOWN",
                confidence=0.40,
                detected_language=lang_res.primary_language,
                secondary_languages=lang_res.secondary_languages,
                is_multilingual=lang_res.is_mixed_script,
                warnings=["Document does not strongly match known clinical category signatures."],
            )

        best_category = max(scores, key=scores.get)
        matched_count = len(evidence_spans.get(best_category, []))
        confidence = min(0.98, max(0.60, 0.60 + (matched_count * 0.10)))

        return DocumentClassificationResult(
            category=best_category,
            confidence=round(confidence, 2),
            detected_language=lang_res.primary_language,
            secondary_languages=lang_res.secondary_languages,
            is_multilingual=lang_res.is_mixed_script,
            evidence_spans=evidence_spans.get(best_category, [])[:5],
        )


document_classifier = ClinicalDocumentClassifier()
