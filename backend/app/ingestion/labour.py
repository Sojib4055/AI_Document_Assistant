from __future__ import annotations

import shutil
from pathlib import Path

import fitz
import pytesseract
from PIL import Image, ImageOps

from .pages import PageText
from .text import clean_text


DOCUMENT_ID = "bangladesh-labour-act-handbook"
DOCUMENT_TITLE = "A Handbook on the Bangladesh Labour Act, 2006"

# The PDF contains front matter, so printed and physical page numbers differ.
PAGE_RANGES = {
    "II": {printed: printed + 17 for printed in range(25, 33)},
    "IX": {printed: printed + 17 for printed in range(56, 61)},
}


def _ocr_page(page: fitz.Page, dpi: int) -> str:
    if not shutil.which("tesseract"):
        raise RuntimeError(
            "Tesseract is required to process the scanned Labour Act pages. "
            "Install tesseract-ocr or keep the supplied OCR cache."
        )

    scale = dpi / 72
    pixmap = page.get_pixmap(
        matrix=fitz.Matrix(scale, scale),
        colorspace=fitz.csGRAY,
        alpha=False,
    )
    image = Image.frombytes("L", [pixmap.width, pixmap.height], pixmap.samples)
    image = ImageOps.autocontrast(image)
    return pytesseract.image_to_string(
        image,
        lang="eng",
        config="--oem 1 --psm 6 -c preserve_interword_spaces=1",
    )


def extract_labour_pages(
    pdf_path: Path,
    ocr_cache_dir: Path,
    *,
    dpi: int = 220,
    force_ocr: bool = False,
) -> list[PageText]:
    if not pdf_path.exists():
        raise FileNotFoundError(f"Missing source document: {pdf_path}")

    ocr_cache_dir.mkdir(parents=True, exist_ok=True)
    document = fitz.open(pdf_path)
    pages: list[PageText] = []

    for chapter, page_map in PAGE_RANGES.items():
        for printed_page, pdf_page in page_map.items():
            cache_path = ocr_cache_dir / f"page_{pdf_page}.txt"
            if cache_path.exists() and not force_ocr:
                raw = cache_path.read_text(encoding="utf-8")
            else:
                page = document[pdf_page - 1]
                embedded = page.get_text("text").strip()
                raw = embedded if len(embedded) >= 50 else _ocr_page(page, dpi)
                cache_path.write_text(raw, encoding="utf-8")

            pages.append(
                PageText(
                    document_id=DOCUMENT_ID,
                    document_title=DOCUMENT_TITLE,
                    source_category="law_handbook",
                    printed_page=printed_page,
                    pdf_page=pdf_page,
                    chapter=chapter,
                    text=clean_text(raw),
                    ocr_used=True,
                )
            )

    return pages
