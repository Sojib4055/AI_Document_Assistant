from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.models.document import Chunk


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def chunks() -> list[Chunk]:
    path = PROJECT_ROOT / "data" / "processed" / "chunks.jsonl"
    return [
        Chunk.from_dict(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
