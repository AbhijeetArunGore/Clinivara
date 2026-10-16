"""
Clinical Document Chunker preserving table rows, units, reference intervals, and section context.
Never slices mid-number, mid-unit, or separates lab parameters from reference intervals.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from clinivara.nlp.preprocessing import MultilingualClinicalPreprocessor
from clinivara.nlp.section_detection import ClinicalSectionDetector


class DocumentChunk(BaseModel):
    """Atomic evidence chunk with provenance metadata."""
    model_config = ConfigDict(frozen=True)

    chunk_id: str
    document_id: str
    tenant_id: str
    page_number: int = Field(ge=1, default=1)
    section_name: Optional[str] = None
    chunk_type: Literal["SECTION_TEXT", "TABLE_ROW", "SUMMARY_STATEMENT"] = "SECTION_TEXT"
    text: str
    token_count_approx: int = Field(ge=1)


class ClinicalDocumentChunker:
    """Semantic chunker respecting clinical section hierarchies and tabular observation boundaries."""

    def __init__(self):
        self.section_detector = ClinicalSectionDetector()
        self.preprocessor = MultilingualClinicalPreprocessor()

    def chunk_document(
        self,
        document_id: str,
        tenant_id: str,
        text: str,
        page_number: int = 1,
    ) -> List[DocumentChunk]:
        """
        Split approved clinical text into bounded evidence chunks.
        """
        chunks: List[DocumentChunk] = []
        if not text or not text.strip():
            return chunks

        # 1. Segment by detected clinical sections
        sections = self.section_detector.segment_sections(text)
        chunk_idx = 1

        for sec in sections:
            sec_name = sec.section_type
            content = sec.content.strip()
            if not content:
                continue

            lines = content.splitlines()
            table_row_buffer = []

            for line in lines:
                line_str = line.strip()
                if not line_str:
                    continue

                # Check if line resembles a tabular observation (has number or colon)
                is_table_like = (
                    any(char.isdigit() for char in line_str)
                    and any(delim in line_str for delim in [":", "\t", "  ", "|", "-", "—"])
                )

                if is_table_like:
                    # Keep tabular observations as atomic units
                    chunks.append(
                        DocumentChunk(
                            chunk_id=f"chk-{chunk_idx}",
                            document_id=document_id,
                            tenant_id=tenant_id,
                            page_number=page_number,
                            section_name=sec_name,
                            chunk_type="TABLE_ROW",
                            text=line_str,
                            token_count_approx=len(line_str.split()),
                        )
                    )
                    chunk_idx += 1
                else:
                    # Non-tabular prose: segment by sentences without splitting decimals
                    sentences = self.preprocessor.segment_sentences(line_str)
                    for sent in sentences:
                        sent_str = sent.strip()
                        if len(sent_str) < 5:
                            continue
                        chunks.append(
                            DocumentChunk(
                                chunk_id=f"chk-{chunk_idx}",
                                document_id=document_id,
                                tenant_id=tenant_id,
                                page_number=page_number,
                                section_name=sec_name,
                                chunk_type="SECTION_TEXT",
                                text=sent_str,
                                token_count_approx=len(sent_str.split()),
                            )
                        )
                        chunk_idx += 1

        # Fallback if no sections were recognized
        if not chunks:
            sentences = self.preprocessor.segment_sentences(text)
            for idx, sent in enumerate(sentences, start=1):
                s = sent.strip()
                if s:
                    chunks.append(
                        DocumentChunk(
                            chunk_id=f"chk-{idx}",
                            document_id=document_id,
                            tenant_id=tenant_id,
                            page_number=page_number,
                            section_name="GENERAL",
                            chunk_type="SECTION_TEXT",
                            text=s,
                            token_count_approx=len(s.split()),
                        )
                    )

        return chunks
