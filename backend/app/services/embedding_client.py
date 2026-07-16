from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence

from app.core.config import Settings, get_settings
from app.services.llm_client import PLACEHOLDER_API_KEYS
from app.services.resilience import ResilienceError, execute_resilient


class EmbeddingClientError(RuntimeError):
    """Raised when an embedding call cannot be completed."""


@dataclass(frozen=True)
class EmbeddingResponse:
    vector: list[float]
    model: str
    raw: dict[str, Any] | None = None


class EmbeddingClient(Protocol):
    def embed_text(self, text: str) -> EmbeddingResponse:
        ...

    def embed_texts(self, texts: Sequence[str]) -> list[EmbeddingResponse]:
        ...


def _has_real_api_key(settings: Settings) -> bool:
    return settings.openai_api_key.strip() not in PLACEHOLDER_API_KEYS


def is_embedding_configured(settings: Settings | None = None) -> bool:
    active_settings = settings or get_settings()
    return (
        active_settings.llm_enabled
        and active_settings.llm_provider == "openai"
        and _has_real_api_key(active_settings)
    )


def _response_to_raw(response: Any) -> dict[str, Any] | None:
    if hasattr(response, "model_dump"):
        return response.model_dump()
    if isinstance(response, dict):
        return response
    return None


class DisabledEmbeddingClient:
    def embed_text(self, text: str) -> EmbeddingResponse:
        raise EmbeddingClientError("Embedding client is disabled or not configured")

    def embed_texts(self, texts: Sequence[str]) -> list[EmbeddingResponse]:
        raise EmbeddingClientError("Embedding client is disabled or not configured")


class OpenAIEmbeddingClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if not is_embedding_configured(self.settings):
            raise EmbeddingClientError(
                "OpenAI embedding client requires LLM_ENABLED=true and a real OPENAI_API_KEY"
            )

        from openai import OpenAI

        self._client = OpenAI(
            api_key=self.settings.openai_api_key,
            base_url=self.settings.openai_base_url or None,
            timeout=self.settings.llm_timeout_seconds,
            max_retries=self.settings.llm_max_retries,
        )

    def embed_text(self, text: str) -> EmbeddingResponse:
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: Sequence[str]) -> list[EmbeddingResponse]:
        try:
            response = self._client.embeddings.create(
                model=self.settings.embedding_model,
                input=list(texts),
            )
        except Exception as exc:  # noqa: BLE001
            raise EmbeddingClientError(f"Embedding call failed: {exc}") from exc

        raw = _response_to_raw(response)
        return [
            EmbeddingResponse(
                vector=[float(value) for value in item.embedding],
                model=self.settings.embedding_model,
                raw=raw,
            )
            for item in response.data
        ]


class FakeEmbeddingClient:
    def __init__(self, *, vector: list[float] | None = None, model: str = "fake-embedding") -> None:
        self.vector = vector or [0.0]
        self.model = model
        self.calls: list[str] = []

    def embed_text(self, text: str) -> EmbeddingResponse:
        self.calls.append(text)
        return EmbeddingResponse(vector=list(self.vector), model=self.model, raw={"fake": True})

    def embed_texts(self, texts: Sequence[str]) -> list[EmbeddingResponse]:
        return [self.embed_text(text) for text in texts]


class ResilientEmbeddingClient:
    def __init__(self, delegate: EmbeddingClient, settings: Settings) -> None:
        self.delegate = delegate
        self.settings = settings
        self.component = f"embedding:{settings.llm_provider}:{settings.embedding_model}"

    def _execute(self, operation):
        try:
            return execute_resilient(
                self.component,
                operation,
                settings=self.settings,
                max_concurrency=self.settings.embedding_max_concurrency,
            )
        except ResilienceError as exc:
            raise EmbeddingClientError(
                f"Embedding reliability guard rejected call: {exc}"
            ) from exc

    def embed_text(self, text: str) -> EmbeddingResponse:
        return self._execute(lambda: self.delegate.embed_text(text))

    def embed_texts(self, texts: Sequence[str]) -> list[EmbeddingResponse]:
        return self._execute(lambda: self.delegate.embed_texts(texts))


def build_embedding_client(settings: Settings | None = None) -> EmbeddingClient:
    active_settings = settings or get_settings()
    if is_embedding_configured(active_settings):
        return ResilientEmbeddingClient(OpenAIEmbeddingClient(active_settings), active_settings)
    return DisabledEmbeddingClient()
