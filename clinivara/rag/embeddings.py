"""
Multilingual Embedding providers for RAG retrieval.
Includes lightweight local TF-IDF / Sublinear n-gram vectorizer supporting English, Hindi, and Marathi offline.
"""

from abc import ABC, abstractmethod

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


class EmbeddingProvider(ABC):
    """Abstract interface for dense/sparse text vectorization."""

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        pass

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        pass


class LocalMultilingualEmbedder(EmbeddingProvider):
    """
    Lightweight, deterministic multilingual vectorizer.
    Uses sublinear TF-IDF with character (3-5) and word n-grams across Devanagari and Latin scripts.
    Requires no GPU, no network downloads, and zero third-party API dependencies.
    """

    def __init__(self, max_features: int = 512):
        self.max_features = max_features
        # Word + Char-wb analyzer captures both Latin prefixes/suffixes and Devanagari root stems
        self.vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            max_features=self.max_features,
            sublinear_tf=True,
        )
        self._is_fitted = False

    def fit(self, texts: list[str]) -> None:
        """Fit vocabulary on the provided document corpus."""
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            valid_texts = ["medical observation clinical finding normal reference"]
        self.vectorizer.fit(valid_texts)
        self._is_fitted = True

    def embed_text(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not self._is_fitted:
            self.fit(texts)

        clean_texts = [t if t and t.strip() else "empty" for t in texts]
        matrix = self.vectorizer.transform(clean_texts)
        dense = matrix.toarray()

        # L2-normalize vectors for cosine similarity dot-product
        norms = np.linalg.norm(dense, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized = dense / norms
        return normalized.tolist()
