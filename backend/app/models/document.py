from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Chunk:
    chunk_id: str
    document_id: str
    document_title: str
    source_category: str
    text: str
    printed_page: int
    pdf_page: int
    section_title: str
    section_number: str = ""
    chapter: str = ""
    ocr_used: bool = False
    is_partial: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        extra = data.pop("extra")
        data.update(extra)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Chunk":
        known = {
            "chunk_id",
            "document_id",
            "document_title",
            "source_category",
            "text",
            "printed_page",
            "pdf_page",
            "section_title",
            "section_number",
            "chapter",
            "ocr_used",
            "is_partial",
        }
        extra = {key: value for key, value in data.items() if key not in known}
        values = {key: data.get(key) for key in known}
        values["section_number"] = values.get("section_number") or ""
        values["chapter"] = values.get("chapter") or ""
        values["ocr_used"] = bool(values.get("ocr_used"))
        values["is_partial"] = bool(values.get("is_partial"))
        values["extra"] = extra
        return cls(**values)  # type: ignore[arg-type]

    def retrieval_text(self) -> str:
        return f"{self.document_title}\n{self.section_title}\n{self.text}"

    def chroma_metadata(self) -> dict[str, str | int | bool]:
        return {
            "document_id": self.document_id,
            "document_title": self.document_title,
            "source_category": self.source_category,
            "printed_page": self.printed_page,
            "pdf_page": self.pdf_page,
            "section_title": self.section_title,
            "section_number": self.section_number,
            "chapter": self.chapter,
            "ocr_used": self.ocr_used,
            "is_partial": self.is_partial,
        }


@dataclass(slots=True)
class RetrievedChunk:
    chunk: Chunk
    dense_rank: int | None = None
    sparse_rank: int | None = None
    dense_distance: float | None = None
    fused_score: float = 0.0
    token_overlap: float = 0.0
