"""
Tesseract OCR engine with language configuration, defensive timeouts,
and quality metric extraction.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from PIL import Image

from clinivara.core.config import settings
from clinivara.core.errors import ExtractionError


class OCREngine:
    """Tesseract OCR wrapper with defensive execution and confidence extraction."""

    def __init__(self):
        self.language = settings.ocr_default_language
        self.timeout = settings.ocr_timeout_seconds

    def extract_from_image_path(self, image_path: Path) -> Tuple[str, Optional[float], Dict[str, Any]]:
        """
        Run OCR on an image file.
        Returns:
            (extracted_text, average_confidence, quality_signals)
        """
        import pytesseract

        try:
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")

                # Extract data containing word-level confidences
                data = pytesseract.image_to_data(
                    img,
                    lang=self.language,
                    timeout=self.timeout,
                    output_type=pytesseract.Output.DICT,
                )

                # Extract text
                text = pytesseract.image_to_string(
                    img,
                    lang=self.language,
                    timeout=self.timeout,
                )

                # Calculate true mean confidence across detected word tokens (ignoring empty or -1)
                confidences = [
                    int(c) for c in data.get("conf", [])
                    if str(c).isdigit() and int(c) >= 0
                ]

                avg_conf = None
                if confidences:
                    avg_conf = round(sum(confidences) / len(confidences), 2)

                quality_signals = {
                    "token_count": len(confidences),
                    "confidence_available": avg_conf is not None,
                    "engine": "Tesseract",
                    "language": self.language,
                }

                return text.strip(), avg_conf, quality_signals

        except pytesseract.TesseractNotFoundError:
            raise ExtractionError(
                "Tesseract OCR executable not found on system PATH. Please ensure Tesseract is installed."
            )
        except Exception as e:
            # Avoid leaking raw text in exception messages
            raise ExtractionError(f"OCR execution failed: {type(e).__name__}")


ocr_engine = OCREngine()
