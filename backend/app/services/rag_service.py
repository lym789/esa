from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import and_, case, cast, exists, func, or_
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.document_department_acl import DocumentDepartmentACL
from app.models.document_role_acl import DocumentRoleACL
from app.models.user import User
from app.services.embedding_client import (
    EmbeddingClient,
    EmbeddingClientError,
    build_embedding_client,
    is_embedding_configured,
)
from app.services.rag_query_service import normalize_query
from app.services.rag_ranking_service import (
    HeuristicReranker,
    RerankCandidate,
    Reranker,
    reciprocal_rank_fusion,
    select_context_ids,
)
from app.services.rag_security_service import detect_prompt_injection
from app.services.resilience import execute_resilient
from app.services.rag_runtime import (
    SearchDiagnostics,
    get_rag_revision,
    query_embedding_cache,
    retrieval_cache,
    runtime_metrics,
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
    dense_score: float = 0.0
    lexical_score: float = 0.0
    fusion_score: float = 0.0
    rerank_score: float = 0.0


@dataclass(frozen=True)
class SearchExecution:
    results: list[SearchResult]
    diagnostics: SearchDiagnostics


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


def embed_texts_for_model(
    texts: list[str],
    *,
    embedding_client: EmbeddingClient | None = None,
    settings: Settings | None = None,
) -> list[TextEmbedding]:
    if not texts:
        return []
    active_settings = settings or get_settings()
    if is_embedding_configured(active_settings):
        try:
            client = embedding_client or build_embedding_client(active_settings)
            responses = client.embed_texts(texts)
            if len(responses) != len(texts):
                raise EmbeddingClientError("Embedding batch response length did not match input")
            return [TextEmbedding(vector=response.vector, model=response.model) for response in responses]
        except (EmbeddingClientError, AttributeError):
            pass
    return [_local_text_embedding(text) for text in texts]


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
    active_settings = settings or get_settings()
    use_cache = active_settings.rag_cache_enabled and embedding_client is None

    def cached_embedding(model: str) -> list[float] | None:
        if not use_cache:
            return None
        value = query_embedding_cache.get((model, normalize_query(query)))
        return [float(item) for item in value] if value is not None else None

    def cache_embedding(model: str, vector: list[float]) -> None:
        if use_cache:
            query_embedding_cache.set(
                (model, normalize_query(query)),
                vector,
                ttl_seconds=active_settings.rag_cache_ttl_seconds,
                max_entries=active_settings.rag_cache_max_entries,
            )

    if LOCAL_EMBEDDING_MODEL in target_models:
        local_cached = cached_embedding(LOCAL_EMBEDDING_MODEL)
        if local_cached is None:
            local_cached = embed_text(query)
            cache_embedding(LOCAL_EMBEDDING_MODEL, local_cached)
        embeddings[LOCAL_EMBEDDING_MODEL] = local_cached

    if active_settings.embedding_model not in target_models:
        return embeddings
    if not is_embedding_configured(active_settings):
        return embeddings

    remote_cached = cached_embedding(active_settings.embedding_model)
    if remote_cached is not None:
        embeddings[active_settings.embedding_model] = remote_cached
        return embeddings

    try:
        client = embedding_client or build_embedding_client(active_settings)
        response = client.embed_text(query)
    except EmbeddingClientError:
        return embeddings

    embeddings[response.model] = response.vector
    cache_embedding(response.model, response.vector)
    return embeddings


def document_access_conditions(
    *,
    user: User | None = None,
    knowledge_base_id: str | None = None,
) -> list[Any]:
    now = datetime.now(timezone.utc)
    conditions: list[Any] = [
        Document.status == "completed",
        Document.publication_status == "published",
        or_(Document.effective_at.is_(None), Document.effective_at <= now),
        or_(Document.expires_at.is_(None), Document.expires_at > now),
    ]
    if knowledge_base_id is not None:
        conditions.append(Document.knowledge_base_id == knowledge_base_id)

    # Internal maintenance and tests may omit a user. All user-facing APIs pass
    # the authenticated user and therefore enforce this filter in the database.
    if user is None or user.role == "admin":
        return conditions

    role_grant = exists().where(
        and_(
            DocumentRoleACL.document_id == Document.id,
            DocumentRoleACL.role == user.role,
        )
    )
    department_grant = (
        exists().where(
            and_(
                DocumentDepartmentACL.document_id == Document.id,
                DocumentDepartmentACL.department_id == user.department_id,
            )
        )
        if user.department_id
        else False
    )
    conditions.append(
        or_(
            Document.visibility.in_({"public", "authenticated"}),
            and_(Document.visibility == "restricted", or_(role_grant, department_grant)),
        )
    )
    return conditions


def current_document_chunk_condition() -> Any:
    return or_(
        and_(Document.current_version_id.is_(None), DocumentChunk.document_version_id.is_(None)),
        and_(
            Document.current_version_id.is_not(None),
            DocumentChunk.document_version_id == Document.current_version_id,
        ),
    )


def _search_result(
    *,
    chunk: DocumentChunk,
    document: Document,
    similarity: float,
    dense_score: float = 0.0,
    lexical_score: float = 0.0,
) -> SearchResult:
    metadata = _load_metadata(chunk)
    metadata.update(
        {
            "chunk_uid": chunk.chunk_uid,
            "document_version_id": chunk.document_version_id,
            "token_count": chunk.token_count or max(1, len(chunk.content) // 2),
        }
    )
    return SearchResult(
        chunk_id=chunk.id,
        document_id=document.id,
        document_name=document.original_filename,
        content=chunk.content,
        page=chunk.page,
        section=chunk.section,
        similarity=similarity,
        metadata=metadata,
        dense_score=dense_score,
        lexical_score=lexical_score,
    )


def _search_postgresql(
    *,
    db: Session,
    query: str,
    top_k: int,
    threshold: float,
    conditions: list[Any],
    embedding_client: EmbeddingClient | None,
    settings: Settings | None,
) -> list[SearchResult]:
    target_models = {
        model
        for (model,) in (
            db.query(DocumentChunk.embedding_model)
            .join(Document, DocumentChunk.document_id == Document.id)
            .filter(
                *conditions,
                current_document_chunk_condition(),
                DocumentChunk.embedding_vector.is_not(None),
            )
            .distinct()
            .all()
        )
        if model
    }
    query_embeddings = _query_embeddings_for_models(
        query,
        target_models,
        embedding_client=embedding_client,
        settings=settings,
    )

    results: list[SearchResult] = []
    for model, query_embedding in query_embeddings.items():
        if not query_embedding:
            continue
        vector_column = cast(DocumentChunk.embedding_vector, Vector(len(query_embedding)))
        distance = vector_column.cosine_distance(query_embedding)
        similarity = (1.0 - distance).label("similarity")
        rows = (
            db.query(DocumentChunk, Document, similarity)
            .join(Document, DocumentChunk.document_id == Document.id)
            .filter(
                *conditions,
                current_document_chunk_condition(),
                DocumentChunk.embedding_model == model,
                DocumentChunk.embedding_vector.is_not(None),
                similarity >= threshold,
            )
            .order_by(distance.asc())
            .limit(top_k)
            .all()
        )
        results.extend(
            _search_result(
                chunk=chunk,
                document=document,
                similarity=float(score),
                dense_score=float(score),
            )
            for chunk, document, score in rows
        )

    return sorted(results, key=lambda item: item.similarity, reverse=True)[:top_k]


def _search_in_memory(
    *,
    db: Session,
    query: str,
    top_k: int,
    threshold: float,
    conditions: list[Any],
    embedding_client: EmbeddingClient | None,
    settings: Settings | None,
) -> list[SearchResult]:
    rows = (
        db.query(DocumentChunk, Document)
        .join(Document, DocumentChunk.document_id == Document.id)
        .filter(*conditions, current_document_chunk_condition())
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
            _search_result(
                chunk=chunk,
                document=document,
                similarity=similarity,
                dense_score=similarity,
            )
        )

    return sorted(results, key=lambda item: item.similarity, reverse=True)[:top_k]


def lexical_similarity(query: str, content: str) -> float:
    query_tokens = {token for token, _weight in _tokenize(normalize_query(query))}
    content_tokens = {token for token, _weight in _tokenize(normalize_query(content))}
    if not query_tokens:
        return 0.0
    overlap = len(query_tokens & content_tokens) / len(query_tokens)
    exact_bonus = 0.2 if normalize_query(query).lower() in normalize_query(content).lower() else 0.0
    return min(1.0, overlap + exact_bonus)


def _search_lexical_postgresql(
    *,
    db: Session,
    query: str,
    top_k: int,
    min_score: float,
    conditions: list[Any],
) -> list[SearchResult]:
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    contains = DocumentChunk.content.ilike(f"%{escaped}%", escape="\\")
    trigram_score = func.similarity(func.lower(DocumentChunk.content), query.lower())
    lexical_score = func.greatest(trigram_score, case((contains, 1.0), else_=0.0)).label(
        "lexical_score"
    )
    rows = (
        db.query(DocumentChunk, Document, lexical_score)
        .join(Document, DocumentChunk.document_id == Document.id)
        .filter(
            *conditions,
            current_document_chunk_condition(),
            lexical_score >= min_score,
        )
        .order_by(lexical_score.desc(), DocumentChunk.id.asc())
        .limit(top_k)
        .all()
    )
    return [
        _search_result(
            chunk=chunk,
            document=document,
            similarity=float(score),
            lexical_score=float(score),
        )
        for chunk, document, score in rows
    ]


def _search_lexical_in_memory(
    *,
    db: Session,
    query: str,
    top_k: int,
    min_score: float,
    conditions: list[Any],
) -> list[SearchResult]:
    rows = (
        db.query(DocumentChunk, Document)
        .join(Document, DocumentChunk.document_id == Document.id)
        .filter(*conditions, current_document_chunk_condition())
        .all()
    )
    results: list[SearchResult] = []
    for chunk, document in rows:
        score = lexical_similarity(query, chunk.content)
        if score < min_score:
            continue
        results.append(
            _search_result(
                chunk=chunk,
                document=document,
                similarity=score,
                lexical_score=score,
            )
        )
    return sorted(results, key=lambda item: (-item.lexical_score, item.chunk_id))[:top_k]


def _fuse_rerank_and_select(
    *,
    query: str,
    dense_results: list[SearchResult],
    lexical_results: list[SearchResult],
    top_k: int,
    settings: Settings,
    reranker: Reranker | None,
) -> tuple[list[SearchResult], bool, int]:
    original_candidate_ids = {result.chunk_id for result in [*dense_results, *lexical_results]}
    dense_results = [result for result in dense_results if not detect_prompt_injection(result.content).blocked]
    lexical_results = [
        result for result in lexical_results if not detect_prompt_injection(result.content).blocked
    ]
    safe_candidate_ids = {result.chunk_id for result in [*dense_results, *lexical_results]}
    filtered_injection_count = len(original_candidate_ids - safe_candidate_ids)
    by_id = {result.chunk_id: result for result in [*dense_results, *lexical_results]}
    dense_scores = {result.chunk_id: result.dense_score for result in dense_results}
    lexical_scores = {result.chunk_id: result.lexical_score for result in lexical_results}
    fusion_scores = reciprocal_rank_fusion(
        [result.chunk_id for result in dense_results],
        [result.chunk_id for result in lexical_results],
        rrf_k=settings.rag_rrf_k,
    )
    raw_candidates = [
        RerankCandidate(
            chunk_id=chunk_id,
            document_id=result.document_id,
            content=result.content,
            token_count=max(1, int(result.metadata.get("token_count", len(result.content) // 2))),
            dense_score=dense_scores.get(chunk_id, 0.0),
            lexical_score=lexical_scores.get(chunk_id, 0.0),
            fusion_score=fusion_scores.get(chunk_id, 0.0),
        )
        for chunk_id, result in by_id.items()
    ]
    deduplicated: dict[str, RerankCandidate] = {}
    for candidate in raw_candidates:
        fingerprint = hashlib.sha256(normalize_query(candidate.content).encode("utf-8")).hexdigest()
        existing = deduplicated.get(fingerprint)
        candidate_rank = (
            candidate.fusion_score,
            candidate.dense_score,
            candidate.lexical_score,
        )
        existing_rank = (
            existing.fusion_score,
            existing.dense_score,
            existing.lexical_score,
        ) if existing is not None else (-1.0, -1.0, -1.0)
        if candidate_rank > existing_rank:
            deduplicated[fingerprint] = candidate
    candidates = list(deduplicated.values())
    active_reranker = reranker or HeuristicReranker()
    reranker_fallback = False
    try:
        if reranker is None:
            reranked = active_reranker.rerank(query, candidates)
        else:
            component = (
                f"reranker:{active_reranker.__class__.__module__}."
                f"{active_reranker.__class__.__qualname__}"
            )
            reranked = execute_resilient(
                component,
                lambda: active_reranker.rerank(query, candidates),
                settings=settings,
                max_concurrency=settings.reranker_max_concurrency,
            )
    except Exception:  # noqa: BLE001 - an optional provider must degrade safely
        reranker_fallback = True
        reranked = HeuristicReranker().rerank(query, candidates)
    rerank_scores = {item.chunk_id: item.score for item in reranked if item.chunk_id in by_id}
    ranked_candidates = sorted(
        candidates,
        key=lambda item: (-rerank_scores.get(item.chunk_id, 0.0), item.chunk_id),
    )
    selected_ids = select_context_ids(
        ranked_candidates,
        rerank_scores,
        top_k=top_k,
        token_budget=settings.rag_context_token_budget,
        max_chunks_per_document=settings.rag_max_chunks_per_document,
        mmr_lambda=settings.rag_mmr_lambda,
    )
    results = [
        replace(
            by_id[chunk_id],
            similarity=max(dense_scores.get(chunk_id, 0.0), lexical_scores.get(chunk_id, 0.0)),
            dense_score=dense_scores.get(chunk_id, 0.0),
            lexical_score=lexical_scores.get(chunk_id, 0.0),
            fusion_score=fusion_scores.get(chunk_id, 0.0),
            rerank_score=rerank_scores.get(chunk_id, 0.0),
        )
        for chunk_id in selected_ids
    ]
    return results, reranker_fallback, filtered_injection_count


def search_with_diagnostics(
    db: Session,
    query: str,
    top_k: int = 5,
    similarity_threshold: float | None = None,
    embedding_client: EmbeddingClient | None = None,
    settings: Settings | None = None,
    user: User | None = None,
    knowledge_base_id: str | None = None,
    reranker: Reranker | None = None,
) -> SearchExecution:
    total_started = perf_counter()
    normalized_query = normalize_query(query)
    active_settings = settings or get_settings()
    if not normalized_query or top_k <= 0:
        diagnostics = SearchDiagnostics(
            timings_ms={"total": round((perf_counter() - total_started) * 1000, 3)}
        )
        runtime_metrics.observe(diagnostics, max_samples=active_settings.rag_metrics_max_samples)
        return SearchExecution([], diagnostics)

    threshold = 0.0 if similarity_threshold is None else similarity_threshold
    candidate_k = max(top_k, active_settings.rag_candidate_k)
    cache_allowed = (
        active_settings.rag_cache_enabled
        and embedding_client is None
        and reranker is None
    )
    revision = get_rag_revision(db)
    user_scope = (
        user.id if user is not None else None,
        user.role if user is not None else None,
        user.department_id if user is not None else None,
    )
    cache_key = (
        id(db.get_bind()),
        revision,
        normalized_query,
        top_k,
        threshold,
        knowledge_base_id,
        user_scope,
        active_settings.embedding_model,
        active_settings.rag_candidate_k,
        active_settings.rag_rrf_k,
        active_settings.rag_lexical_min_score,
        active_settings.rag_max_chunks_per_document,
        active_settings.rag_context_token_budget,
        active_settings.rag_mmr_lambda,
    )
    if cache_allowed:
        cached_results = retrieval_cache.get(cache_key)
        if cached_results is not None:
            diagnostics = SearchDiagnostics(
                cache_hit=True,
                selected_count=len(cached_results),
                timings_ms={"total": round((perf_counter() - total_started) * 1000, 3)},
            )
            runtime_metrics.observe(
                diagnostics,
                max_samples=active_settings.rag_metrics_max_samples,
            )
            return SearchExecution(cached_results, diagnostics)

    conditions = document_access_conditions(
        user=user,
        knowledge_base_id=knowledge_base_id,
    )

    dense_started = perf_counter()
    if db.get_bind().dialect.name == "postgresql":
        dense_results = _search_postgresql(
            db=db,
            query=normalized_query,
            top_k=candidate_k,
            threshold=threshold,
            conditions=conditions,
            embedding_client=embedding_client,
            settings=active_settings,
        )
        dense_ms = (perf_counter() - dense_started) * 1000
        lexical_started = perf_counter()
        lexical_results = _search_lexical_postgresql(
            db=db,
            query=normalized_query,
            top_k=candidate_k,
            min_score=active_settings.rag_lexical_min_score,
            conditions=conditions,
        )
    else:
        dense_results = _search_in_memory(
            db=db,
            query=normalized_query,
            top_k=candidate_k,
            threshold=threshold,
            conditions=conditions,
            embedding_client=embedding_client,
            settings=active_settings,
        )
        dense_ms = (perf_counter() - dense_started) * 1000
        lexical_started = perf_counter()
        lexical_results = _search_lexical_in_memory(
            db=db,
            query=normalized_query,
            top_k=candidate_k,
            min_score=active_settings.rag_lexical_min_score,
            conditions=conditions,
        )
    lexical_ms = (perf_counter() - lexical_started) * 1000
    ranking_started = perf_counter()
    results, reranker_fallback, filtered_injection_count = _fuse_rerank_and_select(
        query=normalized_query,
        dense_results=dense_results,
        lexical_results=lexical_results,
        top_k=top_k,
        settings=active_settings,
        reranker=reranker,
    )
    ranking_ms = (perf_counter() - ranking_started) * 1000
    diagnostics = SearchDiagnostics(
        dense_candidates=len(dense_results),
        lexical_candidates=len(lexical_results),
        selected_count=len(results),
        filtered_injection_count=filtered_injection_count,
        degraded_components=("reranker",) if reranker_fallback else (),
        timings_ms={
            "dense_retrieval": round(dense_ms, 3),
            "lexical_retrieval": round(lexical_ms, 3),
            "ranking_context": round(ranking_ms, 3),
            "total": round((perf_counter() - total_started) * 1000, 3),
        },
    )
    if cache_allowed:
        retrieval_cache.set(
            cache_key,
            results,
            ttl_seconds=active_settings.rag_cache_ttl_seconds,
            max_entries=active_settings.rag_cache_max_entries,
        )
    runtime_metrics.observe(diagnostics, max_samples=active_settings.rag_metrics_max_samples)
    return SearchExecution(results, diagnostics)


def search(
    db: Session,
    query: str,
    top_k: int = 5,
    similarity_threshold: float | None = None,
    embedding_client: EmbeddingClient | None = None,
    settings: Settings | None = None,
    user: User | None = None,
    knowledge_base_id: str | None = None,
    reranker: Reranker | None = None,
) -> list[SearchResult]:
    return search_with_diagnostics(
        db=db,
        query=query,
        top_k=top_k,
        similarity_threshold=similarity_threshold,
        embedding_client=embedding_client,
        settings=settings,
        user=user,
        knowledge_base_id=knowledge_base_id,
        reranker=reranker,
    ).results


def format_citations(results: list[SearchResult]) -> list[str]:
    citations: list[str] = []
    for index, result in enumerate(results, start=1):
        location = f"第 {result.page} 页" if result.page else "未知页码"
        if result.section:
            location = f"{location}，{result.section}"
        citations.append(f"[{index}] {result.document_name}，{location}")
    return citations
