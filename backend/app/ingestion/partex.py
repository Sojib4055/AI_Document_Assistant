from __future__ import annotations

from pathlib import Path

import fitz

from .pages import PageText
from .text import clean_text


DOCUMENT_ID = "partex-star-employee-handbook"
DOCUMENT_TITLE = "Partex Star Group Employee Handbook"


def extract_partex_pages(pdf_path: Path) -> list[PageText]:
    if not pdf_path.exists():
        raise FileNotFoundError(f"Missing source document: {pdf_path}")

    document = fitz.open(pdf_path)
    pages: list[PageText] = []

    # Physical pages 2-6 are landscape spreads. Each half is a printed page.
    for pdf_page in range(2, 7):
        page = document[pdf_page - 1]
        rect = page.rect
        clips = (
            fitz.Rect(rect.x0, rect.y0, rect.x0 + rect.width / 2, rect.y1),
            fitz.Rect(rect.x0 + rect.width / 2, rect.y0, rect.x1, rect.y1),
        )
        for side, clip in enumerate(clips):
            printed_page = (pdf_page - 2) * 2 + side + 1
            raw = page.get_text("text", clip=clip, sort=True)
            text = clean_text(raw, remove_handbook_footer=True)
            pages.append(
                PageText(
                    document_id=DOCUMENT_ID,
                    document_title=DOCUMENT_TITLE,
                    source_category="company_policy",
                    printed_page=printed_page,
                    pdf_page=pdf_page,
                    text=text,
                    ocr_used=False,
                )
            )

    return pages
