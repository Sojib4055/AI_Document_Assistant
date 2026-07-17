from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class SourceReference(BaseModel):
    id: str
    document_id: str
    document: str
    printed_page: int
    pdf_page: int
    section: str
    snippet: str
    source_category: str


class QueryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answerable: bool
    answer: str
    sources: list[SourceReference]
    request_id: str


class DocumentSummary(BaseModel):
    document_id: str
    title: str
    source_category: str
    page_count: int
    chunk_count: int
    scope: str


class HealthResponse(BaseModel):
    status: str
    detail: str | None = None
