"""
Defensive PDF inspector and digital text extractor using PyMuPDF.
"""

from pathlib import Path
from typing import Dict, List, Tuple
import fitz  # PyMuPDF

from clinivara.core.config import settings
from clinivara.core.errors import ExtractionError


class PDFInspector:
    """Inspects PDFs, extracts digital text, and renders selective OCR fallback pages."""

    @staticmethod
    def inspect_and_extract_digital(pdf_path: Path) -> List[Tuple[int, str, bool]]:
        """
        Extracts digital text page-by-page.
        Returns:
            List of (page_num, digital_text, requires_ocr)
        """
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            raise ExtractionError(f"Failed to open PDF document: {type(e).__name__}")

        page_results = []
        try:
            for page_index in range(doc.page_count):
                page = doc[page_index]
                page_num = page_index + 1

                # Extract embedded digital text
                text = page.get_text("text").strip()

                # Determine if page is empty or low-text requiring OCR
                requires_ocr = len(text) < settings.ocr_fallback_char_threshold

                page_results.append((page_num, text, requires_ocr))

            return page_results
        finally:
            doc.close()

    @staticmethod
    def render_page_to_image(pdf_path: Path, page_num: int, output_image_path: Path) -> Path:
        """
        Render a single PDF page to a high-resolution raster image (300 DPI)
        for selective OCR processing. Output saved in Boundary B scratch.
        """
        try:
            doc = fitz.open(pdf_path)
            try:
                page_index = page_num - 1
                if page_index < 0 or page_index >= doc.page_count:
                    raise ExtractionError(f"Requested page {page_num} out of bounds.")

                page = doc[page_index]
                # Render at 300 DPI (approx zoom factor 4.16 from 72 DPI)
                zoom = settings.ocr_dpi / 72.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                pix.save(str(output_image_path))
                return output_image_path
            finally:
                doc.close()
        except Exception as e:
            raise ExtractionError(f"Failed to render PDF page {page_num} for OCR: {type(e).__name__}")


pdf_inspector = PDFInspector()
