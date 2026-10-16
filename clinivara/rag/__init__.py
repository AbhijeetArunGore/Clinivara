"""
Clinical Retrieval-Augmented Generation (RAG) package.
"""

from clinivara.rag.chunking import ClinicalDocumentChunker, DocumentChunk
from clinivara.rag.citations import CitationManager
from clinivara.rag.embeddings import EmbeddingProvider, LocalMultilingualEmbedder
from clinivara.rag.indexing import DocumentIndexManager, IsolatedDocumentIndex, document_index_manager
from clinivara.rag.retrieval import ClinicalRetriever

__all__ = [
    "CitationManager",
    "ClinicalDocumentChunker",
    "ClinicalRetriever",
    "DocumentChunk",
    "DocumentIndexManager",
    "EmbeddingProvider",
    "IsolatedDocumentIndex",
    "LocalMultilingualEmbedder",
    "document_index_manager",
]
