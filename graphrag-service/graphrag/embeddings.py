"""Embedding providers."""

from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod
from collections import Counter

import numpy as np

from graphrag.constants import HASH_EMBEDDING_DIM, TFIDF_MAX_FEATURES

_TOKEN_PATTERN = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_PATTERN.findall(text.lower())


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> np.ndarray:
        """Return matrix shape (n, dim)."""


class TfidfEmbeddingProvider(EmbeddingProvider):
    def __init__(self, max_features: int = TFIDF_MAX_FEATURES) -> None:
        self.max_features = max_features
        self._vocab: dict[str, int] = {}
        self._idf: np.ndarray | None = None
        self._fitted = False

    def _fit(self, corpus_tokens: list[list[str]]) -> None:
        doc_freq: Counter[str] = Counter()

        for tokens in corpus_tokens:
            for token in set(tokens):
                doc_freq[token] += 1

        doc_count = len(corpus_tokens)
        sorted_terms = sorted(
            doc_freq.keys(),
            key=lambda term: (-doc_freq[term], term),
        )[: self.max_features]
        self._vocab = {term: index for index, term in enumerate(sorted_terms)}
        self._idf = np.array(
            [
                math.log((1 + doc_count) / (1 + doc_freq[term])) + 1.0
                for term in sorted_terms
            ],
            dtype=np.float32,
        )
        self._fitted = True

    def _doc_vector(self, tokens: list[str]) -> np.ndarray:
        if self._idf is None:
            raise RuntimeError("TF-IDF provider is not fitted")

        vector = np.zeros(len(self._vocab), dtype=np.float32)
        term_freq = Counter(tokens)

        for term, count in term_freq.items():
            if term in self._vocab:
                vector[self._vocab[term]] = count

        vector *= self._idf
        norm = np.linalg.norm(vector)

        if norm > 0:
            vector /= norm

        return vector

    def fit_corpus(self, texts: list[str]) -> None:
        self._fit([tokenize(text) for text in texts])

    def embed(self, texts: list[str]) -> np.ndarray:
        if not self._fitted:
            self.fit_corpus(texts)

        return np.vstack([self._doc_vector(tokenize(text)) for text in texts])


class HashEmbeddingProvider(EmbeddingProvider):
    dim = HASH_EMBEDDING_DIM

    def embed(self, texts: list[str]) -> np.ndarray:
        matrix = np.zeros((len(texts), self.dim), dtype=np.float32)

        for row, text in enumerate(texts):
            for token in tokenize(text):
                digest = int(hashlib.md5(token.encode()).hexdigest(), 16)
                matrix[row, digest % self.dim] += 1.0

            norm = np.linalg.norm(matrix[row])

            if norm > 0:
                matrix[row] /= norm

        return matrix
