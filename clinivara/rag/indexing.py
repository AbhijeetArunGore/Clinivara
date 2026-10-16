"""
Tenant- and Document-Isolated Vector Index.
Strictly isolates evidence indices per (tenant_id, document_id) to prevent cross-tenant data leakage.
"""

from typing import Dict, List, Optional, Tuple
import numpy as np

from clinivara.rag.chunking import DocumentChunk
from clinivara.rag.embeddings import EmbeddingProvider, LocalMultilingualEmbedder


class IsolatedDocumentIndex:
    """In-memory vector store isolated strictly by tenant_id and document_id."""

    def __init__(self, tenant_id: str, document_id: str, embedder: Optional[EmbeddingProvider] = None):
        self.tenant_id = tenant_id
        self.document_id = document_id
        self.embedder = embedder or LocalMultilingualEmbedder()
        self.chunks: List[DocumentChunk] = []
        self.vectors: Optional[np.ndarray] = None

    def build_index(self, chunks: List[DocumentChunk]) -> None:
        """Populate index with chunks strictly belonging to this tenant and document."""
        # Enforce tenant isolation invariant
        valid_chunks = [
            c for c in chunks if c.tenant_id == self.tenant_id and c.document_id == self.document_id
        ]
        self.chunks = valid_chunks
        if not self.chunks:
            self.vectors = None
            return

        texts = [c.text for c in self.chunks]
        if isinstance(self.embedder, LocalMultilingualEmbedder):
            self.embedder.fit(texts)

        vector_list = self.embedder.embed_batch(texts)
        self.vectors = np.array(vector_list, dtype=np.float32)

    def search(self, query: str, top_k: int = 3) -> List[Tuple[DocumentChunk, float]]:
        """
        Cosine similarity search within this document's isolated index.
        Returns List of (DocumentChunk, similarity_score).
        """
        if not self.chunks or self.vectors is None or len(self.vectors) == 0:
            return []

        query_vec = np.array(self.embedder.embed_text(query), dtype=np.float32)
        # Cosine similarity (vectors are already L2 normalized)
        scores = np.dot(self.vectors, query_vec)

        # Rank indices by descending similarity
        ranked_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in ranked_indices:
            score = float(scores[idx])
            results.append((self.chunks[idx], score))
        return results


class DocumentIndexManager:
    """Manages active isolated document indices."""

    def __init__(self):
        # Key: (tenant_id, document_id) -> IsolatedDocumentIndex
        self._registry: Dict[Tuple[str, str], IsolatedDocumentIndex] = {}

    def get_or_create_index(
        self,
        tenant_id: str,
        document_id: str,
        chunks: Optional[List[DocumentChunk]] = None,
    ) -> IsolatedDocumentIndex:
        key = (tenant_id, document_id)
        if key not in self._registry:
            index = IsolatedDocumentIndex(tenant_id=tenant_id, document_id=document_id)
            if chunks:
                index.build_index(chunks)
            self._registry[key] = index
        elif chunks:
            self._registry[key].build_index(chunks)
        return self._registry[key]

    def clear_index(self, tenant_id: str, document_id: str) -> bool:
        key = (tenant_id, document_id)
        if key in self._registry:
            del self._registry[key]
            return True
        return False


document_index_manager = DocumentIndexManager()
