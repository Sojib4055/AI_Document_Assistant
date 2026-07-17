from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import get_settings
from app.ingestion.pipeline import build_corpus


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the document corpus and metadata.")
    parser.add_argument("--rebuild", action="store_true", help="Remove the existing Chroma index.")
    parser.add_argument("--force-ocr", action="store_true", help="Ignore cached OCR text.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    if args.rebuild and settings.chroma_dir.exists():
        shutil.rmtree(settings.chroma_dir)
    chunks = build_corpus(settings, force_ocr=args.force_ocr)
    print(f"Wrote {len(chunks)} chunks to {settings.processed_chunks_path}")


if __name__ == "__main__":
    main()
