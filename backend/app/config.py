from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Enterprise AI Document Assistant"
    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    data_dir: Path = PROJECT_ROOT / "data"
    source_dir: Path = PROJECT_ROOT / "data" / "source"
    processed_chunks_path: Path = PROJECT_ROOT / "data" / "processed" / "chunks.jsonl"
    manifest_path: Path = PROJECT_ROOT / "data" / "processed" / "manifest.json"
    chroma_dir: Path = PROJECT_ROOT / "data" / "chroma"
    collection_name: str = "employee_policy_chunks"

    openai_api_key: str | None = None
    llm_provider: Literal["auto", "openai", "vertex", "extractive"] = "vertex"
    embedding_provider: Literal["auto", "openai", "vertex", "hash"] = "vertex"
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    google_application_credentials: Path | None = PROJECT_ROOT / "gcp-credentials.json"
    gcp_credentials_json: str | None = None
    gcp_project_id: str | None = None
    gcp_location: str = "us-central1"
    model_name: str = "gemini-2.5-flash"
    vertex_embedding_model: str = "gemini-embedding-001"
    vertex_embedding_dimensions: int = Field(default=768, ge=128, le=3072)
    hash_embedding_dimensions: int = Field(default=768, ge=128, le=4096)

    dense_results: int = Field(default=8, ge=1, le=30)
    sparse_results: int = Field(default=8, ge=1, le=30)
    final_results: int = Field(default=6, ge=1, le=12)
    rrf_constant: int = Field(default=60, ge=1)
    minimum_overlap: float = Field(default=0.08, ge=0.0, le=1.0)
    minimum_query_coverage: float = Field(default=0.60, ge=0.0, le=1.0)

    auto_ingest: bool = True
    cors_origins: list[str] = ["http://localhost:5173"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def vertex_project_id(self) -> str | None:
        if self.gcp_project_id:
            return self.gcp_project_id
        payload = self.vertex_credentials_info
        if payload:
            project_id = payload.get("project_id")
            if project_id:
                return str(project_id)
        path = self.google_application_credentials
        if not path or not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        project_id = payload.get("project_id")
        return str(project_id) if project_id else None

    @property
    def vertex_credentials_info(self) -> dict[str, object] | None:
        if not self.gcp_credentials_json:
            return None
        try:
            payload = json.loads(self.gcp_credentials_json)
        except (TypeError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    @property
    def vertex_configured(self) -> bool:
        path = self.google_application_credentials
        has_file = bool(path and path.is_file())
        return bool(self.vertex_project_id and (self.vertex_credentials_info or has_file))

    @property
    def effective_embedding_provider(self) -> Literal["openai", "vertex", "hash"]:
        if self.embedding_provider == "openai":
            return "openai"
        if self.embedding_provider == "vertex":
            return "vertex"
        if self.embedding_provider == "hash":
            return "hash"
        return "openai" if self.openai_api_key else "hash"

    @property
    def effective_llm_provider(self) -> Literal["openai", "vertex", "extractive"]:
        if self.llm_provider == "openai":
            return "openai"
        if self.llm_provider == "vertex":
            return "vertex"
        if self.llm_provider == "extractive":
            return "extractive"
        return "openai" if self.openai_api_key else "extractive"


@lru_cache
def get_settings() -> Settings:
    return Settings()
