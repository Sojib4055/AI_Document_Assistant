from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import chromadb

from app.models.document import Chunk

from .embeddings import Embedder


class VectorStore:
    def __init__(self, path: Path, collection_name: str) -> None:
        self.path = path
        self.collection_name = collection_name
        self.path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(path))
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self.index_manifest = path / "index_manifest.json"

    @staticmethod
    def fingerprint(chunks: list[Chunk], embedder_name: str) -> str:
        digest = hashlib.sha256(embedder_name.encode("utf-8"))
        for chunk in chunks:
            digest.update(chunk.chunk_id.encode("utf-8"))
            digest.update(chunk.text.encode("utf-8"))
        return digest.hexdigest()

    def _current_fingerprint(self) -> str | None:
        if not self.index_manifest.exists():
            return None
        try:
            data = json.loads(self.index_manifest.read_text(encoding="utf-8"))
            return data.get("fingerprint")
        except (json.JSONDecodeError, OSError):
            return None

    def rebuild(self, chunks: list[Chunk], embedder: Embedder) -> None:
        expected = self.fingerprint(chunks, embedder.name)
        if self._current_fingerprint() == expected and self.collection.count() == len(chunks):
            return

        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        batch_size = 64
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            embeddings = embedder.embed([chunk.retrieval_text() for chunk in batch])
            self.collection.upsert(
                ids=[chunk.chunk_id for chunk in batch],
                embeddings=embeddings,
                documents=[chunk.text for chunk in batch],
                metadatas=[chunk.chroma_metadata() for chunk in batch],
            )

        self.index_manifest.write_text(
            json.dumps(
                {
                    "fingerprint": expected,
                    "embedding_provider": embedder.name,
                    "chunk_count": len(chunks),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def query(
        self,
        query_embedding: list[float],
        limit: int,
    ) -> list[tuple[str, float]]:
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            include=["distances"],
        )
        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]
        return [(chunk_id, float(distance)) for chunk_id, distance in zip(ids, distances)]
