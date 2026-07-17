from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol

from openai import OpenAI
from google import genai
from google.genai import types
from google.oauth2 import service_account

from app.models.document import RetrievedChunk

from .tokenizer import tokenize


REFUSAL_TEXT = (
    "I don't have sufficient information in the provided documents to answer this question."
)


@dataclass(slots=True)
class GenerationResult:
    answerable: bool
    answer: str
    citation_ids: list[str]


class Generator(Protocol):
    def generate(self, question: str, evidence: list[RetrievedChunk]) -> GenerationResult:
        ...


def _source_block(evidence: list[RetrievedChunk]) -> str:
    blocks: list[str] = []
    for index, item in enumerate(evidence, start=1):
        chunk = item.chunk
        section = chunk.section_title
        if chunk.section_number:
            section = f"Section {chunk.section_number} - {section}"
        blocks.append(
            "\n".join(
                [
                    f"[S{index}]",
                    f"Document: {chunk.document_title}",
                    f"Source type: {chunk.source_category}",
                    f"Printed page: {chunk.printed_page}",
                    f"Section: {section}",
                    f"Text: {chunk.text}",
                ]
            )
        )
    return "\n\n".join(blocks)


class OpenAIGenerator:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model

    @staticmethod
    def _parse_json(text: str) -> dict[str, object]:
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                return json.loads(text[start : end + 1])
            raise

    def generate(self, question: str, evidence: list[RetrievedChunk]) -> GenerationResult:
        allowed_ids = {f"S{index}" for index in range(1, len(evidence) + 1)}
        instructions = """
You answer employee policy questions using only the supplied evidence.
Do not use outside knowledge. Do not guess missing facts.
Treat company policy and the Labour Act handbook as separate authorities.
When both are relevant and differ, present them under separate labels instead of merging them.
Keep the answer concise and practical: normally 2-4 short sentences and no more
than 100 words. Give only the facts needed to answer the question. For long
lists, use compact semicolon-separated items without repeating the evidence.
Return JSON only with this shape:
{"answerable": true, "answer": "...", "citation_ids": ["S1"]}
If the evidence does not answer the question, set answerable to false, use the exact refusal sentence, and return an empty citation_ids list.
""".strip()
        prompt = f"Question:\n{question}\n\nEvidence:\n{_source_block(evidence)}"
        response = self.client.responses.create(
            model=self.model,
            instructions=instructions,
            input=prompt,
            max_output_tokens=700,
        )
        payload = self._parse_json(response.output_text)
        answerable = bool(payload.get("answerable"))
        answer = str(payload.get("answer") or "").strip()
        raw_ids = payload.get("citation_ids") or []
        citation_ids = [str(item) for item in raw_ids if str(item) in allowed_ids]

        if not answerable:
            return GenerationResult(False, REFUSAL_TEXT, [])
        if not answer or not citation_ids:
            return GenerationResult(False, REFUSAL_TEXT, [])
        return GenerationResult(True, answer, citation_ids)


class VertexGenerator:
    def __init__(
        self,
        credentials_path: str | None,
        credentials_info: dict[str, object] | None,
        project: str,
        location: str,
        model: str,
    ) -> None:
        scopes = ["https://www.googleapis.com/auth/cloud-platform"]
        if credentials_info:
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=scopes,
            )
        elif credentials_path:
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=scopes,
            )
        else:
            raise ValueError("Vertex AI credentials are not configured.")
        self.client = genai.Client(
            vertexai=True,
            project=project,
            location=location,
            credentials=credentials,
            http_options=types.HttpOptions(api_version="v1"),
        )
        self.model = model

    def generate(self, question: str, evidence: list[RetrievedChunk]) -> GenerationResult:
        allowed_ids = {f"S{index}" for index in range(1, len(evidence) + 1)}
        instructions = """
Answer employee policy questions using only the supplied evidence.
Do not use outside knowledge or guess missing facts.
Treat company policy and the Labour Act handbook as separate authorities.
Keep the answer concise and practical: normally 2-4 short sentences and no more
than 100 words. Give only the facts needed to answer the question. For long
lists, use compact semicolon-separated items without repeating the evidence.
Cite only the supplied source IDs.
""".strip()
        response = self.client.models.generate_content(
            model=self.model,
            contents=f"Question:\n{question}\n\nEvidence:\n{_source_block(evidence)}",
            config=types.GenerateContentConfig(
                system_instruction=instructions,
                response_mime_type="application/json",
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "answerable": {"type": "BOOLEAN"},
                        "answer": {"type": "STRING"},
                        "citation_ids": {"type": "ARRAY", "items": {"type": "STRING"}},
                    },
                    "required": ["answerable", "answer", "citation_ids"],
                },
                max_output_tokens=2048,
                temperature=0.1,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        try:
            payload = json.loads(response.text or "{}")
        except (json.JSONDecodeError, TypeError):
            return GenerationResult(False, REFUSAL_TEXT, [])
        answer = str(payload.get("answer") or "").strip()
        citation_ids = [
            str(item) for item in (payload.get("citation_ids") or [])
            if str(item) in allowed_ids
        ]
        if not bool(payload.get("answerable")) or not answer or not citation_ids:
            return GenerationResult(False, REFUSAL_TEXT, [])
        return GenerationResult(True, answer, citation_ids)


class ExtractiveGenerator:
    @staticmethod
    def _best_sentences(question: str, text: str, limit: int = 2) -> list[str]:
        query_tokens = set(tokenize(question))
        text = text.replace("i.e.", "that is").replace("e.g.", "for example")
        sentences = re.split(r"(?<=[.!?;])\s+|\n+", text)
        ranked: list[tuple[float, str]] = []
        for sentence in sentences:
            sentence = re.sub(r"\s+", " ", sentence).strip(" -")
            if len(sentence) < 25:
                continue
            tokens = set(tokenize(sentence))
            score = len(tokens & query_tokens) / max(len(query_tokens), 1)
            if score:
                ranked.append((score, sentence))
        ranked.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
        return [sentence for _, sentence in ranked[:limit]]

    def generate(self, question: str, evidence: list[RetrievedChunk]) -> GenerationResult:
        compare = any(word in question.lower() for word in ("compare", "difference", "versus", " vs ", "both"))

        if compare:
            selected: dict[str, tuple[int, list[str]]] = {}
            for index, item in enumerate(evidence, start=1):
                category = item.chunk.source_category
                if category in selected:
                    continue
                sentences = self._best_sentences(question, item.chunk.text, limit=2)
                if sentences:
                    selected[category] = (index, sentences)
            if len(selected) >= 2:
                parts: list[str] = []
                citations: list[str] = []
                labels = {
                    "company_policy": "Partex policy",
                    "law_handbook": "Labour Act handbook",
                }
                for category in ("company_policy", "law_handbook"):
                    if category not in selected:
                        continue
                    index, sentences = selected[category]
                    parts.append(f"{labels[category]}: {' '.join(sentences)}")
                    citations.append(f"S{index}")
                return GenerationResult(True, "\n\n".join(parts), citations)

        candidates: list[tuple[float, int, list[str]]] = []
        query_tokens = set(tokenize(question))
        for index, item in enumerate(evidence, start=1):
            sentences = self._best_sentences(question, item.chunk.text, limit=3)
            if not sentences:
                continue
            title_tokens = set(tokenize(item.chunk.section_title))
            title_score = len(query_tokens & title_tokens) / max(len(title_tokens), 1)
            candidates.append((item.fused_score * 20 + item.token_overlap + title_score, index, sentences))

        if candidates:
            _, index, sentences = max(candidates, key=lambda item: item[0])
            return GenerationResult(True, " ".join(sentences), [f"S{index}"])
        return GenerationResult(False, REFUSAL_TEXT, [])
