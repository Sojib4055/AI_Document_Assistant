from __future__ import annotations

import re
import unicodedata


LIGATURES = str.maketrans(
    {
        "ﬁ": "fi",
        "ﬂ": "fl",
        "ﬀ": "ff",
        "ﬃ": "ffi",
        "ﬄ": "ffl",
        "–": "-",
        "—": "-",
        "’": "'",
        "“": '"',
        "”": '"',
        "•": "-",
    }
)


def clean_text(raw: str, *, remove_handbook_footer: bool = False) -> str:
    text = unicodedata.normalize("NFKC", raw).translate(LIGATURES)
    text = text.replace("\r", "\n").replace("\u00ad", "")
    text = re.sub(r"(?<=\w)-\s*\n\s*(?=[a-z])", "", text)
    text = re.sub(r"[ \t]+", " ", text)

    cleaned_lines: list[str] = []
    for original_line in text.splitlines():
        line = original_line.strip()
        if not line:
            cleaned_lines.append("")
            continue
        if remove_handbook_footer and re.fullmatch(
            r"(?:\d+\s*)?employee handbook|\d+", line, re.IGNORECASE
        ):
            continue
        if re.fullmatch(r"\d{1,3}", line):
            continue
        cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" +\n", "\n", text)
    text = re.sub(r"\n +", "\n", text)
    return text.strip()


def compact_paragraphs(text: str) -> str:
    """Join wrapped PDF lines without flattening headings and list items."""

    lines = [line.strip() for line in text.splitlines()]
    paragraphs: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            paragraphs.append(" ".join(current).strip())
            current.clear()

    for line in lines:
        if not line:
            flush()
            continue

        is_heading = bool(
            re.match(r"^(?:CHAPTER\b|[A-L]\.\s|\d{1,3}[.,]\s+[A-Z])", line)
        )
        is_list_item = bool(re.match(r"^(?:\([a-z0-9]+\)|[a-z]\)|-\s)", line, re.I))

        if is_heading or is_list_item:
            flush()
            current.append(line)
            if is_heading:
                flush()
            continue

        current.append(line)

    flush()
    return "\n\n".join(paragraphs)


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "section"


def sentence_snippet(text: str, limit: int = 260) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= limit:
        return normalized
    shortened = normalized[:limit].rsplit(" ", 1)[0]
    return shortened + "..."
