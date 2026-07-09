from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.embedding_client import (
    EmbeddingClient,
    EmbeddingClientError,
    build_embedding_client,
    is_embedding_configured,
)


LOCAL_EMBEDDING_MODEL = "local-hash-v1"
LOCAL_EMBEDDING_DIMENSIONS = 256


@dataclass(frozen=True)
class SearchResult:
    chunk_id: int
    document_id: int
    document_name: str
    content: str
    page: int | None
    section: str | None
    similarity: float
    metadata: dict[str, Any]


@dataclass(frozen=True)
class TextEmbedding:
    vector: list[float]
    model: str


def _tokenize(text: str) -> list[tuple[str, float]]:
    lowered = text.lower()
    ascii_tokens = [(f"ascii:{token}", 4.0) for token in re.findall(r"[a-z0-9]+", lowered)]
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", lowered)
    cjk_single_tokens = [(f"cjk:{char}", 0.4) for char in cjk_chars]
    cjk_bigram_tokens = [(f"cjk2:{left}{right}", 3.0) for left, right in zip(cjk_chars, cjk_chars[1:])]
    return ascii_tokens + cjk_bigram_tokens + cjk_single_tokens


def _token_index(token: str) -> int:
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % LOCAL_EMBEDDING_DIMENSIONS


def embed_text(text: str) -> list[float]:
    vector = [0.0] * LOCAL_EMBEDDING_DIMENSIONS
    tokens = _tokenize(text)
    if not tokens:
        return vector

    for token, weight in tokens:
        vector[_token_index(token)] += weight

    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude == 0:
        return vector

    return [value / magnitude for value in vector]


def embed_chunks(chunks: list[str]) -> list[list[float]]:
    return [embed_text(chunk) for chunk in chunks]


def _local_text_embedding(text: str) -> TextEmbedding:
    return TextEmbedding(vector=embed_text(text), model=LOCAL_EMBEDDING_MODEL)


def embed_text_for_model(
    text: str,
    *,
    embedding_client: EmbeddingClient | None = None,
    settings: Settings | None = None,
) -> TextEmbedding:
    active_settings = settings or get_settings()
    if is_embedding_configured(active_settings):
        try:
            client = embedding_client or build_embedding_client(active_settings)
            response = client.embed_text(text)
            return TextEmbedding(vector=response.vector, model=response.model)
        except EmbeddingClientError:
            return _local_text_embedding(text)
    return _local_text_embedding(text)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(left_value * right_value for left_value, right_value in zip(left, right))


def _load_embedding(chunk: DocumentChunk) -> list[float]:
    if not chunk.embedding_json:
        return embed_text(chunk.content)
    try:
        embedding = json.loads(chunk.embedding_json)
    except json.JSONDecodeError:
        return embed_text(chunk.content)
    if not isinstance(embedding, list):
        return embed_text(chunk.content)
    return [float(value) for value in embedding]


def _load_metadata(chunk: DocumentChunk) -> dict[str, Any]:
    try:
        metadata = json.loads(chunk.metadata_json)
    except json.JSONDecodeError:
        return {}
    return metadata if isinstance(metadata, dict) else {}


def _chunk_embedding_model(chunk: DocumentChunk) -> str:
    return chunk.embedding_model or LOCAL_EMBEDDING_MODEL


def _query_embeddings_for_models(
    query: str,
    target_models: set[str],
    *,
    embedding_client: EmbeddingClient | None = None,
    settings: Settings | None = None,
) -> dict[str, list[float]]:
    embeddings: dict[str, list[float]] = {}
    if LOCAL_EMBEDDING_MODEL in target_models:
        embeddings[LOCAL_EMBEDDING_MODEL] = embed_text(query)

    active_settings = settings or get_settings()
    if active_settings.embedding_model not in target_models:
        return embeddings
    if not is_embedding_configured(active_settings):
        return embeddings

    try:
        client = embedding_client or build_embedding_client(active_settings)
        response = client.embed_text(query)
    except EmbeddingClientError:
        return embeddings

    embeddings[response.model] = response.vector
    return embeddings


def search(
    db: Session,
    query: str,
    top_k: int = 5,
    similarity_threshold: float | None = None,
    embedding_client: EmbeddingClient | None = None,
    settings: Settings | None = None,
) -> list[SearchResult]:
    if not query.strip() or top_k <= 0:
        return []

    threshold = 0.0 if similarity_threshold is None else similarity_threshold
    rows = (
        db.query(DocumentChunk, Document)
        .join(Document, DocumentChunk.document_id == Document.id)
        .filter(Document.status == "completed")
        .all()
    )
    target_models = {_chunk_embedding_model(chunk) for chunk, _document in rows}
    query_embeddings = _query_embeddings_for_models(
        query,
        target_models,
        embedding_client=embedding_client,
        settings=settings,
    )

    results: list[SearchResult] = []
    for chunk, document in rows:
        chunk_model = _chunk_embedding_model(chunk)
        query_embedding = query_embeddings.get(chunk_model)
        if query_embedding is None:
            continue
        similarity = cosine_similarity(query_embedding, _load_embedding(chunk))
        if similarity < threshold:
            continue
        results.append(
            SearchResult(
                chunk_id=chunk.id,
                document_id=document.id,
                document_name=document.original_filename,
                content=chunk.content,
                page=chunk.page,
                section=chunk.section,
                similarity=similarity,
                metadata=_load_metadata(chunk),
            )
        )

    return sorted(results, key=lambda item: item.similarity, reverse=True)[:top_k]


def format_citations(results: list[SearchResult]) -> list[str]:
    citations: list[str] = []
    for index, result in enumerate(results, start=1):
        location = f"第 {result.page} 页" if result.page else "未知页码"
        if result.section:
            location = f"{location}，{result.section}"
        citations.append(f"[{index}] {result.document_name}，{location}")
    return citations
