from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse

from app.models.schemas import (
    DocumentSummary,
    HealthResponse,
    QueryRequest,
    QueryResponse,
)
from app.services.rag import RagService


router = APIRouter()


def _service(request: Request) -> RagService:
    service = getattr(request.app.state, "rag_service", None)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document service is not initialized.",
        )
    return service


@router.get("/documents", response_model=list[DocumentSummary])
def list_documents(request: Request) -> list[DocumentSummary]:
    return _service(request).list_documents()


@router.get("/documents/{document_id}/file", response_class=FileResponse)
def document_file(document_id: str, request: Request) -> FileResponse:
    settings = _service(request).settings
    files = {
        "partex-star-employee-handbook": settings.source_dir / "Partex-Star-Group.pdf",
        "bangladesh-labour-act-handbook": settings.source_dir / "A Handbook on the Bangladesh Labour Act 2006.pdf",
    }
    path = files.get(document_id)
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="Document not found.")
    return FileResponse(path, media_type="application/pdf", filename=path.name)


@router.post("/query", response_model=QueryResponse)
def query_documents(payload: QueryRequest, request: Request) -> QueryResponse:
    question = payload.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be blank.",
        )
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        return _service(request).query(question, request_id)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.get("/health/ready", response_model=HealthResponse)
def readiness(request: Request) -> HealthResponse:
    service = getattr(request.app.state, "rag_service", None)
    if not service or not service.ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document index is not ready.",
        )
    return HealthResponse(status="ready")
