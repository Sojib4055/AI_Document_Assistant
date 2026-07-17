from __future__ import annotations

import shutil
from pathlib import Path

from app.config import Settings
from app.services.rag import RagService


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def make_service(tmp_path: Path) -> RagService:
    chunks_path = tmp_path / "processed" / "chunks.jsonl"
    chunks_path.parent.mkdir(parents=True)
    shutil.copy(PROJECT_ROOT / "data" / "processed" / "chunks.jsonl", chunks_path)

    settings = Settings(
        app_env="test",
        data_dir=tmp_path,
        source_dir=PROJECT_ROOT / "data" / "source",
        processed_chunks_path=chunks_path,
        manifest_path=tmp_path / "processed" / "manifest.json",
        chroma_dir=tmp_path / "chroma",
        collection_name="rag_service_test",
        embedding_provider="hash",
        llm_provider="extractive",
        auto_ingest=False,
    )
    service = RagService(settings)
    service.initialize()
    return service


def test_answer_contains_source_metadata(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    response = service.query("What are the working hours at Partex?", "test-request")

    assert response.answerable is True
    assert response.sources
    assert response.sources[0].printed_page == 5
    assert response.sources[0].document_id == "partex-star-employee-handbook"


def test_out_of_scope_question_is_refused(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    response = service.query("What is the company's annual revenue?", "test-request")

    assert response.answerable is False
    assert response.sources == []
    assert "sufficient information" in response.answer


def test_generic_sick_leave_question_prefers_company_policy(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    response = service.query(
        "What happens if I am sick for more than seven days?",
        "test-request",
    )

    assert response.answerable is True
    assert response.sources[0].document_id == "partex-star-employee-handbook"
    assert "fitness certificate" in response.answer.lower()


def test_answers_labour_act_casual_leave_question_with_natural_wording(
    tmp_path: Path,
) -> None:
    service = make_service(tmp_path)
    response = service.query(
        "How many days of casual leave does a worker receive?",
        "test-request",
    )

    assert response.answerable is True
    assert response.sources[0].document_id == "bangladesh-labour-act-handbook"
    assert response.sources[0].printed_page == 59


def test_answers_labour_act_rest_interval_question_with_natural_wording(
    tmp_path: Path,
) -> None:
    service = make_service(tmp_path)
    response = service.query(
        "What rest or meal intervals must workers receive?",
        "test-request",
    )

    assert response.answerable is True
    assert response.sources[0].document_id == "bangladesh-labour-act-handbook"
    assert response.sources[0].printed_page == 56


def test_answers_what_actions_are_considered_misconduct(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    response = service.query(
        "What actions are considered misconduct?",
        "test-request",
    )

    assert response.answerable is True
    assert response.sources[0].document_id == "bangladesh-labour-act-handbook"
    assert response.sources[0].printed_page == 31
    assert "misconduct" in response.answer.lower()


def test_answers_how_wages_are_paid_for_unused_leave(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    response = service.query(
        "How are wages paid for unused leave?",
        "test-request",
    )

    assert response.answerable is True
    assert response.sources[0].document_id == "bangladesh-labour-act-handbook"
    assert response.sources[0].printed_page == 28
    assert "wages" in response.answer.lower()
