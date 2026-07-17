from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import Settings, get_settings
from app.models.document import Chunk

from .chunking import chunk_labour, chunk_partex
from .labour import extract_labour_pages
from .partex import extract_partex_pages


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_chunks(path: Path, chunks: list[Chunk]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")


def load_chunks(path: Path) -> list[Chunk]:
    if not path.exists():
        return []
    chunks: list[Chunk] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                chunks.append(Chunk.from_dict(json.loads(line)))
    return chunks


def build_corpus(
    settings: Settings | None = None,
    *,
    force_ocr: bool = False,
) -> list[Chunk]:
    settings = settings or get_settings()
    partex_path = settings.source_dir / "Partex-Star-Group.pdf"
    labour_path = settings.source_dir / "A Handbook on the Bangladesh Labour Act 2006.pdf"
    ocr_cache = settings.processed_chunks_path.parent / "ocr"

    partex_pages = extract_partex_pages(partex_path)
    labour_pages = extract_labour_pages(
        labour_path,
        ocr_cache,
        force_ocr=force_ocr,
    )

    chunks = chunk_partex(partex_pages) + chunk_labour(labour_pages)
    chunks.sort(key=lambda item: (item.document_id, item.pdf_page, item.chunk_id))
    write_chunks(settings.processed_chunks_path, chunks)

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "chunk_count": len(chunks),
        "documents": [
            {
                "document_id": "partex-star-employee-handbook",
                "file": partex_path.name,
                "sha256": _sha256(partex_path),
                "scope": "Full printed pages 1-10",
            },
            {
                "document_id": "bangladesh-labour-act-handbook",
                "file": labour_path.name,
                "sha256": _sha256(labour_path),
                "scope": "Chapter II printed pages 25-32 and Chapter IX printed pages 56-60",
            },
        ],
    }
    settings.manifest_path.parent.mkdir(parents=True, exist_ok=True)
    settings.manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return chunks
