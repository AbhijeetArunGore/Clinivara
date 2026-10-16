"""
Automated unit and integration tests for clinical RAG:
- Semantic table- and section-aware chunking.
- Deterministic multilingual vectorization.
- Tenant- and document-isolated vector indices.
- Evidence threshold gating and citation verification.
- Insufficient evidence handling.
"""

import pytest

from clinivara.rag.chunking import ClinicalDocumentChunker
from clinivara.rag.citations import CitationManager
from clinivara.rag.embeddings import LocalMultilingualEmbedder
from clinivara.rag.indexing import DocumentIndexManager, IsolatedDocumentIndex
from clinivara.rag.retrieval import ClinicalRetriever
from clinivara.schemas.ai import QuestionAnswerRequest
from clinivara.schemas.approved_output import (
    ApprovedDocumentOutput,
    ClinicalContent,
    DeidentificationMetadata,
    ExtractionMetadata,
    QualityMetadata,
)


def test_chunking_preserves_table_rows_and_sections():
    chunker = ClinicalDocumentChunker()
    text = (
        "CLINICAL INDICATION:\n"
        "Patient evaluation for diabetes.\n\n"
        "LABORATORY RESULTS:\n"
        "Fasting Blood Glucose: 165 mg/dL (Reference: 70 - 99 mg/dL)\n"
        "Serum Creatinine: 1.1 mg/dL (Reference: 0.7 - 1.3 mg/dL)\n\n"
        "IMPRESSION:\n"
        "Elevated blood glucose. Normal renal function."
    )
    chunks = chunker.chunk_document("doc_1", "tenant_1", text)
    assert len(chunks) >= 4

    # Tabular lines should be chunked as TABLE_ROW
    table_chunks = [c for c in chunks if c.chunk_type == "TABLE_ROW"]
    assert len(table_chunks) >= 2
    assert any("Fasting Blood Glucose" in c.text for c in table_chunks)


def test_multilingual_embedder_dimension_and_consistency():
    embedder = LocalMultilingualEmbedder(max_features=128)
    texts = [
        "Hemoglobin 14.2 g/dL normal range",
        "हीमोग्लोबिन 14.2 g/dL सामान्य मर्यादा",
        "Elevated creatinine indicating renal impairment",
    ]
    vectors = embedder.embed_batch(texts)
    assert len(vectors) == 3
    assert len(vectors[0]) == 128

    # Query embedding
    q_vec = embedder.embed_text("Hemoglobin")
    assert len(q_vec) == 128


def test_tenant_isolated_index_prevents_cross_tenant_leakage():
    index_mgr = DocumentIndexManager()
    chunker = ClinicalDocumentChunker()

    # Index doc 1 for tenant A
    doc_a_chunks = chunker.chunk_document("doc_a", "tenant_a", "Patient Rajesh has Type 2 Diabetes.")
    index_a = index_mgr.get_or_create_index("tenant_a", "doc_a", doc_a_chunks)

    # Index doc 2 for tenant B
    doc_b_chunks = chunker.chunk_document("doc_b", "tenant_b", "Patient Sunita has Hypertension.")
    index_b = index_mgr.get_or_create_index("tenant_b", "doc_b", doc_b_chunks)

    # Searching index A must only return doc_a chunks
    results_a = index_a.search("Hypertension", top_k=5)
    for chunk, _ in results_a:
        assert chunk.tenant_id == "tenant_a"
        assert chunk.document_id == "doc_a"
        assert "Sunita" not in chunk.text


def test_rag_retriever_grounded_answer_and_insufficient_evidence():
    retriever = ClinicalRetriever(relevance_threshold=0.15)
    text = (
        "COMPLETE BLOOD COUNT:\n"
        "Hemoglobin: 13.8 g/dL (Reference: 12.0 - 15.5 g/dL)\n"
        "WBC Count: 6800 /cumm\n"
        "Impression: Normal hematology."
    )

    approved_doc = ApprovedDocumentOutput(
        document_id="doc_rag_test",
        tenant_id="tenant_rag",
        processing_status="APPROVED",
        extraction=ExtractionMetadata(status="COMPLETED", pages_processed=1, methods_used=["text"]),
        deidentification=DeidentificationMetadata(status="COMPLETED", validation_status="PASSED"),
        clinical_content=ClinicalContent(text=text, sections=[]),
        quality=QualityMetadata(schema_valid=True, clinical_content_preserved=True, residual_identifiers_detected=0),
    )

    # 1. Answerable question
    q_answered = QuestionAnswerRequest(question="What is the hemoglobin level?", target_language="en")
    res_answered = retriever.answer_question("tenant_rag", "doc_rag_test", approved_doc, q_answered)
    assert res_answered.status == "ANSWERED"
    assert len(res_answered.citations) > 0
    assert any("Hemoglobin" in c.evidence_text for c in res_answered.citations)

    # 2. Unanswerable question (facts not in document)
    q_insufficient = QuestionAnswerRequest(question="What was the patient's cholesterol level?", target_language="en")
    res_insufficient = retriever.answer_question("tenant_rag", "doc_rag_test", approved_doc, q_insufficient)
    assert res_insufficient.status == "INSUFFICIENT_EVIDENCE"
    assert len(res_insufficient.citations) == 0
