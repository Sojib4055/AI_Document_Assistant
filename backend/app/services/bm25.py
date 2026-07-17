from __future__ import annotations

import math
from collections import Counter

from app.models.document import Chunk

from .tokenizer import tokenize


class BM25Index:
    def __init__(self, chunks: list[Chunk], *, k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.documents = [tokenize(chunk.retrieval_text()) for chunk in chunks]
        self.term_counts = [Counter(document) for document in self.documents]
        self.lengths = [len(document) for document in self.documents]
        self.average_length = sum(self.lengths) / max(len(self.lengths), 1)
        self.document_frequency: Counter[str] = Counter()
        for document in self.documents:
            self.document_frequency.update(set(document))
        self.vocabulary = set(self.document_frequency)

    def _idf(self, token: str) -> float:
        count = self.document_frequency.get(token, 0)
        total = len(self.documents)
        return math.log(1 + (total - count + 0.5) / (count + 0.5))

    def score(self, query: str, index: int) -> float:
        query_tokens = tokenize(query)
        if not query_tokens or not self.documents[index]:
            return 0.0

        length = self.lengths[index]
        normalizer = self.k1 * (
            1 - self.b + self.b * length / max(self.average_length, 1.0)
        )
        score = 0.0
        counts = self.term_counts[index]
        for token in query_tokens:
            frequency = counts.get(token, 0)
            if not frequency:
                continue
            score += self._idf(token) * (frequency * (self.k1 + 1)) / (
                frequency + normalizer
            )
        return score

    def search(self, query: str, limit: int) -> list[tuple[str, float]]:
        ranked = [
            (chunk.chunk_id, self.score(query, index))
            for index, chunk in enumerate(self.chunks)
        ]
        ranked = [item for item in ranked if item[1] > 0]
        ranked.sort(key=lambda item: item[1], reverse=True)
        return ranked[:limit]


    def unknown_query_terms(self, query: str) -> set[str]:
        return {token for token in tokenize(query) if token not in self.vocabulary}

    def query_coverage(self, query: str) -> float:
        tokens = set(tokenize(query))
        if not tokens:
            return 0.0
        matched = sum(1 for token in tokens if token in self.vocabulary)
        return matched / len(tokens)
