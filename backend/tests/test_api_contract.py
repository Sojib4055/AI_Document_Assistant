from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import router
from app.models.schemas import DocumentSummary, QueryResponse


class FakeService:
    ready = True

    def list_documents(self):
        return [
            DocumentSummary(
                document_id="doc-1",
                title="Example Handbook",
                source_category="company_policy",
                page_count=2,
                chunk_count=3,
                scope="Test scope",
            )
        ]

    def query(self, question: str, request_id: str):
        return QueryResponse(
            answerable=False,
            answer="I don't have sufficient information in the provided documents to answer this question.",
            sources=[],
            request_id=request_id,
        )


def make_client() -> TestClient:
    app = FastAPI()
    app.state.rag_service = FakeService()
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


def test_query_contract() -> None:
    with make_client() as client:
        response = client.post("/api/v1/query", json={"question": "Unknown item"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["answerable"] is False
    assert payload["sources"] == []
    assert "request_id" in payload


def test_short_question_is_rejected() -> None:
    with make_client() as client:
        response = client.post("/api/v1/query", json={"question": "x"})

    assert response.status_code == 422
