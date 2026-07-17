from __future__ import annotations

import hashlib
import math
from typing import Protocol

from openai import OpenAI
from google import genai
from google.genai import types
from google.oauth2 import service_account

from .tokenizer import tokenize


class Embedder(Protocol):
    name: str

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


class HashEmbedder:
    """Small deterministic embedding used when no API key is configured."""

    name = "hash-v1"

    def __init__(self, dimensions: int = 768) -> None:
        self.dimensions = dimensions

    def _vector(self, text: str) -> list[float]:
        tokens = tokenize(text, drop_stop_words=False)
        features = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
        vector = [0.0] * self.dimensions
        for feature in features:
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=16).digest()
            index = int.from_bytes(digest[:8], "big") % self.dimensions
            sign = 1.0 if digest[8] & 1 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            vector = [value / norm for value in vector]
        return vector

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]


class OpenAIEmbedder:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.name = f"openai:{model}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]


class VertexEmbedder:
    def __init__(
        self,
        credentials_path: str | None,
        credentials_info: dict[str, object] | None,
        project: str,
        location: str,
        model: str,
        dimensions: int,
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
        self.dimensions = dimensions
        self.name = f"vertex:{model}:{dimensions}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self.client.models.embed_content(
            model=self.model,
            contents=texts,
            config=types.EmbedContentConfig(output_dimensionality=self.dimensions),
        )
        return [list(item.values or []) for item in (response.embeddings or [])]
