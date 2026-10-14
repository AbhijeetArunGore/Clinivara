"""
Document extraction orchestrator: selective OCR fallback and provenance tracking.
"""

from pathlib import Path
from typing import List

from clinivara.audit.audit_logger import audit_logger
from clinivara.core.config import settings
from clinivara.core.errors import ExtractionError
from clinivara.extraction.models import ExtractionResult, PageExtraction
from clinivara.extraction.ocr_engine import ocr_engine
from clinivara.extraction.pdf_inspector import pdf_inspector
from clinivara.storage.storage_manager import storage_manager


class DocumentExtractor:
    """Orchestrates digital extraction and selective OCR fallback with strict Boundary B isolation."""

    def extract_document(
        self,
        tenant_id: str,
        document_id: str,
        correlation_id: str,
        file_path: Path,
    ) -> ExtractionResult:
        scratch_dir = storage_manager.get_scratch_dir(tenant_id, document_id)
        pages: List[PageExtraction] = []
        methods_used = set()
        warnings = []

        try:
            ext = file_path.suffix.lower()

            if ext == ".pdf":
                # PDF processing: page-by-page digital inspection + selective OCR
                page_data = pdf_inspector.inspect_and_extract_digital(file_path)

                for page_num, digital_text, requires_ocr in page_data:
                    if requires_ocr and settings.ocr_enabled:
                        # Invoke selective OCR fallback
                        methods_used.add("ocr_fallback")
                        scratch_img = scratch_dir / f"page_{page_num}_render.png"

                        try:
                            pdf_inspector.render_page_to_image(file_path, page_num, scratch_img)
                            ocr_text, conf, signals = ocr_engine.extract_from_image_path(scratch_img)

                            # Clean up scratch image immediately
                            if scratch_img.exists():
                                scratch_img.unlink()

                            # Combine if any digital text was present
                            combined_text = digital_text + "\n" + ocr_text if digital_text else ocr_text

                            pages.append(
                                PageExtraction(
                                    page_number=page_num,
                                    method="OCR_FALLBACK",
                                    text=combined_text.strip(),
                                    character_count=len(combined_text.strip()),
                                    word_count=len(combined_text.split()),
                                    ocr_confidence=conf,
                                    warnings=["Triggered selective OCR fallback due to low digital text density."],
                                    quality_signals=signals,
                                )
                            )
                        except Exception as e:
                            warnings.append(f"OCR failed for page {page_num}: {type(e).__name__}")
                            pages.append(
                                PageExtraction(
                                    page_number=page_num,
                                    method="FAILED",
                                    text=digital_text,
                                    character_count=len(digital_text),
                                    word_count=len(digital_text.split()),
                                    ocr_confidence=None,
                                    warnings=[f"OCR fallback error: {str(e)}"],
                                    quality_signals={"error": type(e).__name__},
                                )
                            )
                    else:
                        # Sufficient digital text present
                        methods_used.add("embedded_digital_text")
                        pages.append(
                            PageExtraction(
                                page_number=page_num,
                                method="DIGITAL_TEXT",
                                text=digital_text,
                                character_count=len(digital_text),
                                word_count=len(digital_text.split()),
                                ocr_confidence=None,
                                warnings=[],
                                quality_signals={"digital_text_density": len(digital_text)},
                            )
                        )

            elif ext in (".png", ".jpg", ".jpeg"):
                # Direct raster image document: run OCR
                methods_used.add("image_direct_ocr")
                ocr_text, conf, signals = ocr_engine.extract_from_image_path(file_path)

                pages.append(
                    PageExtraction(
                        page_number=1,
                        method="IMAGE_DIRECT",
                        text=ocr_text,
                        character_count=len(ocr_text),
                        word_count=len(ocr_text.split()),
                        ocr_confidence=conf,
                        warnings=[],
                        quality_signals=signals,
                    )
                )

            else:
                raise ExtractionError(f"Unsupported document extension for extraction: {ext}")

            # Verify extraction yielded text
            total_chars = sum(p.character_count for p in pages)
            if total_chars == 0:
                warnings.append("Document extraction yielded zero characters across all pages.")

            result = ExtractionResult(
                document_id=document_id,
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                pages=pages,
                methods_used=sorted(list(methods_used)),
                total_pages=len(pages),
                warnings=warnings,
                status="COMPLETED" if total_chars > 0 else "PARTIAL",
            )

            # Audit event (never logging raw text)
            audit_logger.record_event(
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                event_type="EXTRACTION_COMPLETED",
                status="SUCCESS",
                document_id=document_id,
                details={
                    "total_pages": len(pages),
                    "methods_used": list(methods_used),
                    "total_characters": total_chars,
                    "warnings_count": len(warnings),
                },
            )

            return result

        finally:
            # Ephemeral scratch cleanup
            storage_manager.cleanup_scratch_dir(tenant_id, document_id)


document_extractor = DocumentExtractor()
