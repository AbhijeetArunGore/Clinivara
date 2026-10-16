"""
Citation Generator and Evidence Provenance Verifier.
Ensures every claim is tied to a verifiable chunk in the source document.
"""

from typing import List, Optional
from clinivara.rag.chunking import DocumentChunk
from clinivara.schemas.ai import Citation


class CitationManager:
    """Creates and audits grounding citations for RAG outputs."""

    @staticmethod
    def create_citation_from_chunk(chunk: DocumentChunk, relevance_score: float = 1.0) -> Citation:
        return Citation(
            citation_id=f"cit-{chunk.chunk_id}",
            source_page=chunk.page_number,
            section_name=chunk.section_name,
            evidence_text=chunk.text,
            relevance_score=round(relevance_score, 4),
        )

    @staticmethod
    def verify_citations(
        citations: List[Citation],
        available_chunks: List[DocumentChunk],
    ) -> List[str]:
        """Verify that citations correspond to known chunks in the document."""
        chunk_texts = {c.text.strip().lower() for c in available_chunks}
        warnings = []

        for cit in citations:
            evidence_clean = cit.evidence_text.strip().lower()
            if evidence_clean not in chunk_texts:
                # Check substring match
                match = any(evidence_clean in ct or ct in evidence_clean for ct in chunk_texts)
                if not match:
                    warnings.append(f"Citation {cit.citation_id} text does not match any indexed chunk.")

        return warnings
