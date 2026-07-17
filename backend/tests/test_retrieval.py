from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.models.document import Chunk
from app.services.embeddings import HashEmbedder
from app.services.retrieval import HybridRetriever
from app.services.vector_store import VectorStore


def make_retriever(tmp_path: Path, chunks: list[Chunk]) -> HybridRetriever:
    settings = Settings(
        app_env="test",
        data_dir=tmp_path,
        source_dir=tmp_path / "source",
        processed_chunks_path=tmp_path / "chunks.jsonl",
        manifest_path=tmp_path / "manifest.json",
        chroma_dir=tmp_path / "chroma",
        embedding_provider="hash",
        llm_provider="extractive",
        auto_ingest=False,
    )
    embedder = HashEmbedder(settings.hash_embedding_dimensions)
    store = VectorStore(settings.chroma_dir, "test_policy_chunks")
    store.rebuild(chunks, embedder)
    return HybridRetriever(chunks, store, embedder, settings)


def test_retrieves_partex_sick_leave_clause(tmp_path: Path, chunks: list[Chunk]) -> None:
    retriever = make_retriever(tmp_path, chunks)
    results = retriever.search("What happens if I am sick for more than seven days?")
    top_ids = {item.chunk.chunk_id for item in results[:3]}

    assert "partex-06-b-leave-2-sick-leave" in top_ids


def test_retrieves_labour_daily_hours(tmp_path: Path, chunks: list[Chunk]) -> None:
    retriever = make_retriever(tmp_path, chunks)
    results = retriever.search("ordinary daily working hours under the Labour Act")
    top_ids = {item.chunk.chunk_id for item in results[:3]}

    assert "labour-chix-s100-p56" in top_ids
