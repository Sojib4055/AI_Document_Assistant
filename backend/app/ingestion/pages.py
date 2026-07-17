from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PageText:
    document_id: str
    document_title: str
    source_category: str
    printed_page: int
    pdf_page: int
    text: str
    chapter: str = ""
    ocr_used: bool = False
