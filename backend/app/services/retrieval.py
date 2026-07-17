from __future__ import annotations

from app.config import Settings
from app.models.document import Chunk, RetrievedChunk

from .bm25 import BM25Index
from .embeddings import Embedder
from .tokenizer import tokenize
from .vector_store import VectorStore


class HybridRetriever:
    def __init__(
        self,
        chunks: list[Chunk],
        vector_store: VectorStore,
        embedder: Embedder,
        settings: Settings,
    ) -> None:
        self.chunks = chunks
        self.by_id = {chunk.chunk_id: chunk for chunk in chunks}
        self.vector_store = vector_store
        self.embedder = embedder
        self.settings = settings
        self.bm25 = BM25Index(chunks)

    @staticmethod
    def _overlap(question: str, chunk: Chunk) -> float:
        query_tokens = set(tokenize(question))
        if not query_tokens:
            return 0.0
        chunk_tokens = set(tokenize(chunk.retrieval_text()))
        return len(query_tokens & chunk_tokens) / len(query_tokens)

    def search(self, question: str) -> list[RetrievedChunk]:
        query_embedding = self.embedder.embed([question])[0]
        dense = self.vector_store.query(query_embedding, self.settings.dense_results)
        sparse = self.bm25.search(question, self.settings.sparse_results)

        combined: dict[str, RetrievedChunk] = {}
        for rank, (chunk_id, distance) in enumerate(dense, start=1):
            chunk = self.by_id.get(chunk_id)
            if not chunk:
                continue
            item = combined.setdefault(chunk_id, RetrievedChunk(chunk=chunk))
            item.dense_rank = rank
            item.dense_distance = distance
            item.fused_score += 1 / (self.settings.rrf_constant + rank)

        for rank, (chunk_id, _) in enumerate(sparse, start=1):
            chunk = self.by_id.get(chunk_id)
            if not chunk:
                continue
            item = combined.setdefault(chunk_id, RetrievedChunk(chunk=chunk))
            item.sparse_rank = rank
            item.fused_score += 1.15 / (self.settings.rrf_constant + rank)

        query_tokens = set(tokenize(question))
        ranked = list(combined.values())
        for item in ranked:
            item.token_overlap = self._overlap(question, item.chunk)
            title_tokens = set(tokenize(item.chunk.section_title))
            title_overlap = len(query_tokens & title_tokens) / max(len(title_tokens), 1)
            document_tokens = set(tokenize(item.chunk.document_title))
            named_source_match = bool(
                query_tokens
                & document_tokens
                & {"partex", "labour", "bangladesh"}
            )
            item.fused_score += item.token_overlap * 0.01
            item.fused_score += title_overlap * 0.025
            if title_tokens and title_tokens.issubset(query_tokens):
                item.fused_score += 0.02
            if named_source_match:
                item.fused_score += 0.04
            law_requested = bool(query_tokens & {"labour", "law", "legal"})
            if not law_requested and item.chunk.source_category == "company_policy":
                item.fused_score += 0.015
        ranked.sort(key=lambda item: item.fused_score, reverse=True)
        return ranked[: self.settings.final_results]

    def query_coverage(self, question: str) -> float:
        return self.bm25.query_coverage(question)

    def unknown_query_terms(self, question: str) -> set[str]:
        return self.bm25.unknown_query_terms(question)
