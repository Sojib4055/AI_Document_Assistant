from __future__ import annotations

import re
from dataclasses import replace

from app.models.document import Chunk

from .pages import PageText
from .text import compact_paragraphs, slugify


PLAIN_PARTEX_HEADINGS = {
    "Message from Chairperson",
    "Purpose of the Handbook",
    "History of the Organization",
    "Partex Star Group Concerns",
    "Vision",
    "Mission - 2020",
    "Our Values and Guiding Principles",
    "Locations",
    "Corporate Office:",
    "Sales Office:",
    "Operating Office:",
    "Factory/ Plant:",
}

TOP_LEVEL_RE = re.compile(r"^([A-L])\.\s+(.+?)\s*$")
NUMBERED_RE = re.compile(r"^(\d+)\.\s+(.+?)\s*:?[ ]*$")
SECTION_PREFIX_RE = re.compile(r"^(\d{1,3})[.,]\s+(.+)$")


def _split_if_large(chunk: Chunk, max_words: int = 650, overlap: int = 80) -> list[Chunk]:
    words = chunk.text.split()
    if len(words) <= max_words:
        return [chunk]

    output: list[Chunk] = []
    start = 0
    part = 1
    while start < len(words):
        end = min(start + max_words, len(words))
        text = " ".join(words[start:end])
        output.append(
            replace(
                chunk,
                chunk_id=f"{chunk.chunk_id}-{part:02d}",
                text=text,
                section_title=f"{chunk.section_title} (part {part})",
            )
        )
        if end == len(words):
            break
        start = max(0, end - overlap)
        part += 1
    return output


def chunk_partex(pages: list[PageText]) -> list[Chunk]:
    chunks: list[Chunk] = []
    current_title = "Introduction"
    current_top = ""
    body: list[str] = []
    start_page = pages[0].printed_page
    start_pdf_page = pages[0].pdf_page
    end_page = start_page

    def flush() -> None:
        nonlocal body
        text = compact_paragraphs("\n".join(body)).strip()
        if not text:
            body = []
            return
        base = Chunk(
            chunk_id=f"partex-{start_page:02d}-{slugify(current_title)}",
            document_id=pages[0].document_id,
            document_title=pages[0].document_title,
            source_category=pages[0].source_category,
            text=text,
            printed_page=start_page,
            pdf_page=start_pdf_page,
            section_title=current_title,
            ocr_used=False,
            extra={"end_printed_page": end_page},
        )
        chunks.extend(_split_if_large(base))
        body = []

    for page in sorted(pages, key=lambda item: item.printed_page):
        end_page = page.printed_page
        for line in page.text.splitlines():
            line = line.strip()
            if not line:
                body.append("")
                continue

            top_match = TOP_LEVEL_RE.match(line)
            numbered_match = NUMBERED_RE.match(line)
            is_plain = line in PLAIN_PARTEX_HEADINGS

            if top_match:
                flush()
                current_top = f"{top_match.group(1)}. {top_match.group(2)}"
                current_title = current_top
                start_page = page.printed_page
                start_pdf_page = page.pdf_page
                continue

            if numbered_match:
                flush()
                number, name = numbered_match.groups()
                name = name.rstrip(":")
                prefix = f"{current_top} - " if current_top else ""
                current_title = f"{prefix}{number}. {name}"
                start_page = page.printed_page
                start_pdf_page = page.pdf_page
                continue

            if is_plain:
                flush()
                current_top = ""
                current_title = line.rstrip(":")
                start_page = page.printed_page
                start_pdf_page = page.pdf_page
                continue

            body.append(line)

    flush()
    return chunks


def _split_legal_heading(line: str) -> tuple[str, str, str] | None:
    match = SECTION_PREFIX_RE.match(line)
    if not match:
        return None

    number, rest = match.groups()
    candidates: list[tuple[int, int]] = []
    for separator in (":", ";", ".-", " - "):
        index = rest.find(separator)
        if index >= 0:
            candidates.append((index, len(separator)))
    if not candidates:
        return None

    index, width = min(candidates, key=lambda item: item[0])
    title = rest[:index].strip().rstrip(".")
    remainder = rest[index + width :].strip()
    return number, title, remainder


def _repair_common_ocr(text: str) -> str:
    replacements = {
        "calender": "calendar",
        "shal]": "shall",
        "shal!": "shall",
        "shail": "shall",
        "badly worker": "badli worker",
        "badly card": "badli card",
        "ete.": "etc.",
        "No women shall": "No woman shall",
        "not Jess than": "not less than",
        "one and half day": "one and a half days",
        "one and a half day in each week": "one and a half days in each week",
        "by: him": "by him",
        "(J)": "(1)",
        "required.cr allowed": "required or allowed",
        "fortyeight": "forty-eight",
        "may be i prescribed": "may be prescribed",
        "Notwithstanding i anything": "Notwithstanding anything",
        "requiring i any": "requiring any",
        "at ; the": "at the",
        "for : such": "for such",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"[|{}]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def chunk_labour(pages: list[PageText]) -> list[Chunk]:
    chunks: list[Chunk] = []
    current_number = ""
    current_title = ""
    current_chapter = ""
    body: list[str] = []
    start_page = 0
    start_pdf_page = 0
    end_page = 0

    def flush() -> None:
        nonlocal body
        if not current_number:
            body = []
            return
        text = _repair_common_ocr(compact_paragraphs("\n".join(body)))
        if not text:
            body = []
            return
        base = Chunk(
            chunk_id=f"labour-ch{current_chapter.lower()}-s{current_number}-p{start_page}",
            document_id=pages[0].document_id,
            document_title=pages[0].document_title,
            source_category=pages[0].source_category,
            text=text,
            printed_page=start_page,
            pdf_page=start_pdf_page,
            section_title=current_title,
            section_number=current_number,
            chapter=current_chapter,
            ocr_used=True,
            is_partial=current_number == "24",
            extra={"end_printed_page": end_page},
        )
        chunks.extend(_split_if_large(base))
        body = []

    for page in sorted(pages, key=lambda item: item.pdf_page):
        end_page = page.printed_page
        for line in page.text.splitlines():
            stripped = line.strip()
            if not stripped:
                body.append("")
                continue
            if stripped.upper().startswith("CHAPTER") or stripped.upper() in {
                "CONDITIONS OF SERVICE AND EMPLOYMENT",
                "WORKING HOURS AND LEAVE",
            }:
                continue

            heading = _split_legal_heading(stripped)
            if heading:
                flush()
                current_number, current_title, remainder = heading
                current_chapter = page.chapter
                start_page = page.printed_page
                start_pdf_page = page.pdf_page
                end_page = page.printed_page
                if remainder:
                    body.append(remainder)
                continue

            if current_number:
                body.append(stripped)

    flush()
    return chunks
