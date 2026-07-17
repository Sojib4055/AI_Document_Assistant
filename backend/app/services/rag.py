from __future__ import annotations

import re
from collections import defaultdict

from app.config import Settings
from app.ingestion.pipeline import build_corpus, load_chunks
from app.ingestion.text import sentence_snippet
from app.models.document import Chunk, RetrievedChunk
from app.models.schemas import DocumentSummary, QueryResponse, SourceReference

from .embeddings import HashEmbedder, OpenAIEmbedder, VertexEmbedder
from .generation import (
    REFUSAL_TEXT,
    ExtractiveGenerator,
    GenerationResult,
    OpenAIGenerator,
    VertexGenerator,
)
from .retrieval import HybridRetriever
from .vector_store import VectorStore


class RagService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.ready = False
        self.chunks: list[Chunk] = []
        self.retriever: HybridRetriever | None = None
        self.generator: OpenAIGenerator | VertexGenerator | ExtractiveGenerator | None = None

    def initialize(self) -> None:
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings.chroma_dir.mkdir(parents=True, exist_ok=True)

        self.chunks = load_chunks(self.settings.processed_chunks_path)
        if not self.chunks:
            if not self.settings.auto_ingest:
                raise RuntimeError("No processed corpus found. Run the ingestion script first.")
            self.chunks = build_corpus(self.settings)

        if self.settings.effective_embedding_provider == "openai":
            if not self.settings.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY is required for OpenAI embeddings.")
            embedder = OpenAIEmbedder(
                self.settings.openai_api_key,
                self.settings.openai_embedding_model,
            )
        elif self.settings.effective_embedding_provider == "vertex":
            if not self.settings.vertex_configured:
                raise RuntimeError("Provide GCP_CREDENTIALS_JSON or a valid GOOGLE_APPLICATION_CREDENTIALS file.")
            credentials_path = self.settings.google_application_credentials
            embedder = VertexEmbedder(
                str(credentials_path) if credentials_path and credentials_path.is_file() else None,
                self.settings.vertex_credentials_info,
                self.settings.vertex_project_id or "",
                self.settings.gcp_location,
                self.settings.vertex_embedding_model,
                self.settings.vertex_embedding_dimensions,
            )
        else:
            embedder = HashEmbedder(self.settings.hash_embedding_dimensions)

        vector_store = VectorStore(
            self.settings.chroma_dir,
            self.settings.collection_name,
        )
        vector_store.rebuild(self.chunks, embedder)
        self.retriever = HybridRetriever(
            self.chunks,
            vector_store,
            embedder,
            self.settings,
        )

        if self.settings.effective_llm_provider == "openai":
            if not self.settings.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY is required for OpenAI generation.")
            self.generator = OpenAIGenerator(
                self.settings.openai_api_key,
                self.settings.openai_chat_model,
            )
        elif self.settings.effective_llm_provider == "vertex":
            if not self.settings.vertex_configured:
                raise RuntimeError("Provide GCP_CREDENTIALS_JSON or a valid GOOGLE_APPLICATION_CREDENTIALS file.")
            credentials_path = self.settings.google_application_credentials
            self.generator = VertexGenerator(
                str(credentials_path) if credentials_path and credentials_path.is_file() else None,
                self.settings.vertex_credentials_info,
                self.settings.vertex_project_id or "",
                self.settings.gcp_location,
                self.settings.model_name,
            )
        else:
            self.generator = ExtractiveGenerator()

        self.ready = True

    def list_documents(self) -> list[DocumentSummary]:
        grouped: dict[str, list[Chunk]] = defaultdict(list)
        for chunk in self.chunks:
            grouped[chunk.document_id].append(chunk)

        scopes = {
            "partex-star-employee-handbook": "Full employee handbook, printed pages 1-10",
            "bangladesh-labour-act-handbook": (
                "Chapter II printed pages 25-32 and Chapter IX printed pages 56-60"
            ),
        }
        documents: list[DocumentSummary] = []
        for document_id, chunks in grouped.items():
            pages = {chunk.printed_page for chunk in chunks}
            documents.append(
                DocumentSummary(
                    document_id=document_id,
                    title=chunks[0].document_title,
                    source_category=chunks[0].source_category,
                    page_count=len(pages),
                    chunk_count=len(chunks),
                    scope=scopes.get(document_id, "Selected document scope"),
                )
            )
        return sorted(documents, key=lambda item: item.title)

    def _refusal(self, request_id: str) -> QueryResponse:
        return QueryResponse(
            answerable=False,
            answer=REFUSAL_TEXT,
            sources=[],
            request_id=request_id,
        )

    @staticmethod
    def _conversational_reply(question: str) -> str | None:
        """Handle simple social messages without sending them through document RAG."""
        normalized = re.sub(r"[^a-z\s']", " ", question.lower())
        normalized = re.sub(r"\s+", " ", normalized).strip()

        if re.fullmatch(r"(thank you|thanks|thank you very much|thanks a lot)", normalized):
            return "You're welcome! Feel free to ask me anything about the available employee policy documents."
        if re.fullmatch(r"(bye|goodbye|see you|see you later|take care)", normalized):
            return "Goodbye! Feel free to return whenever you have a policy question."
        if re.fullmatch(r"(how are you|how are you doing|how's it going)", normalized):
            return "I'm doing well, thank you! How can I help you with the employee policy documents today?"
        if re.fullmatch(
            r"((hi|hello|hey|hiya|greetings|good morning|good afternoon|good evening)( there)?)+",
            normalized,
        ):
            return "Hello! How can I help you with the employee policy documents today?"
        return None

    def query(self, question: str, request_id: str) -> QueryResponse:
        if not self.ready or not self.retriever or not self.generator:
            raise RuntimeError("The document index is not ready.")

        conversational_reply = self._conversational_reply(question)
        if conversational_reply:
            return QueryResponse(
                answerable=True,
                answer=conversational_reply,
                sources=[],
                request_id=request_id,
            )

        evidence = self.retriever.search(question)
        if not evidence:
            return self._refusal(request_id)

        coverage = self.retriever.query_coverage(question)
        unknown_terms = {term for term in self.retriever.unknown_query_terms(question) if len(term) >= 4}
        best_overlap = max(item.token_overlap for item in evidence)
        # A natural-language question may contain an unfamiliar modifier while
        # still matching the evidence strongly. Reject unknown vocabulary only
        # when the known terms cover less than 80% of the query; the previous
        # any-unknown-term rule refused valid paraphrases before generation.
        insufficient_known_terms = bool(unknown_terms) and coverage < 0.80
        if (
            insufficient_known_terms
            or coverage < self.settings.minimum_query_coverage
            or best_overlap < self.settings.minimum_overlap
        ):
            return self._refusal(request_id)

        result = self.generator.generate(question, evidence)
        if not result.answerable:
            return self._refusal(request_id)

        source_map = {
            f"S{index}": item
            for index, item in enumerate(evidence, start=1)
        }
        sources: list[SourceReference] = []
        seen: set[str] = set()
        for source_id in result.citation_ids:
            item = source_map.get(source_id)
            if not item or item.chunk.chunk_id in seen:
                continue
            seen.add(item.chunk.chunk_id)
            chunk = item.chunk
            section = chunk.section_title
            if chunk.section_number:
                section = f"Section {chunk.section_number} - {section}"
            sources.append(
                SourceReference(
                    id=source_id,
                    document_id=chunk.document_id,
                    document=chunk.document_title,
                    printed_page=chunk.printed_page,
                    pdf_page=chunk.pdf_page,
                    section=section,
                    snippet=sentence_snippet(chunk.text),
                    source_category=chunk.source_category,
                )
            )

        if not sources:
            return self._refusal(request_id)

        return QueryResponse(
            answerable=True,
            answer=result.answer,
            sources=sources,
            request_id=request_id,
        )
