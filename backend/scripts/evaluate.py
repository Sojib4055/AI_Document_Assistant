from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import get_settings
from app.services.rag import RagService


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    settings = get_settings()
    service = RagService(settings)
    service.initialize()
    cases = json.loads(
        (PROJECT_ROOT / "evaluation" / "questions.json").read_text(encoding="utf-8")
    )

    results: list[dict[str, object]] = []
    retrieval_hits = 0
    behavior_hits = 0

    for index, case in enumerate(cases, start=1):
        question = case["question"]
        response = service.query(question, f"evaluation-{index}")
        behavior_ok = response.answerable == case["answerable"]
        behavior_hits += int(behavior_ok)

        retrieval_ok = True
        retrieved: list[str] = []
        if case["answerable"]:
            assert service.retriever is not None
            evidence = service.retriever.search(question)
            retrieved = [item.chunk.chunk_id for item in evidence[:5]]
            retrieval_ok = any(
                item.chunk.document_id == case["expected_document"]
                and item.chunk.printed_page == case["expected_page"]
                and (
                    not case.get("expected_section")
                    or item.chunk.section_number == case["expected_section"]
                )
                for item in evidence[:5]
            )
            retrieval_hits += int(retrieval_ok)

        results.append(
            {
                "question": question,
                "answerable": response.answerable,
                "behavior_ok": behavior_ok,
                "retrieval_ok": retrieval_ok,
                "retrieved_top_5": retrieved,
                "answer": response.answer,
                "sources": [source.model_dump() for source in response.sources],
            }
        )

    answerable_cases = sum(1 for case in cases if case["answerable"])
    summary = {
        "retrieval_recall_at_5": retrieval_hits / max(answerable_cases, 1),
        "behavior_accuracy": behavior_hits / len(cases),
        "cases": results,
    }
    output = PROJECT_ROOT / "evaluation" / "results.json"
    output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "cases"}, indent=2))
    print(f"Detailed results written to {output}")


if __name__ == "__main__":
    main()
