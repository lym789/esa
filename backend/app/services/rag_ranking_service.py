from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True)
class RerankCandidate:
    chunk_id: int
    document_id: int
    content: str
    token_count: int
    dense_score: float
    lexical_score: float
    fusion_score: float


@dataclass(frozen=True)
class RerankResult:
    chunk_id: int
    score: float


class Reranker(Protocol):
    def rerank(self, query: str, candidates: Sequence[RerankCandidate]) -> list[RerankResult]:
        ...


class HeuristicReranker:
    """Deterministic default that can be replaced by a cross-encoder provider."""

    def rerank(self, query: str, candidates: Sequence[RerankCandidate]) -> list[RerankResult]:
        del query
        ranked = [
            RerankResult(
                chunk_id=item.chunk_id,
                score=(0.50 * item.dense_score)
                + (0.30 * item.lexical_score)
                + (0.20 * min(1.0, item.fusion_score * 60)),
            )
            for item in candidates
        ]
        return sorted(ranked, key=lambda item: (-item.score, item.chunk_id))


def reciprocal_rank_fusion(
    dense_ids: Sequence[int],
    lexical_ids: Sequence[int],
    *,
    rrf_k: int,
) -> dict[int, float]:
    if rrf_k <= 0:
        raise ValueError("rrf_k must be greater than 0")
    scores: dict[int, float] = {}
    for ranking in (dense_ids, lexical_ids):
        for rank, chunk_id in enumerate(dict.fromkeys(ranking), start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)
    return scores


def _terms(text: str) -> set[str]:
    lowered = text.lower()
    ascii_terms = set(re.findall(r"[a-z0-9]+", lowered))
    cjk = re.findall(r"[\u4e00-\u9fff]", lowered)
    cjk_terms = {left + right for left, right in zip(cjk, cjk[1:])}
    return ascii_terms | cjk_terms


def _content_similarity(left: str, right: str) -> float:
    left_terms = _terms(left)
    right_terms = _terms(right)
    union = left_terms | right_terms
    return len(left_terms & right_terms) / len(union) if union else 0.0


def select_context_ids(
    ranked: Sequence[RerankCandidate],
    rerank_scores: dict[int, float],
    *,
    top_k: int,
    token_budget: int,
    max_chunks_per_document: int,
    mmr_lambda: float,
) -> list[int]:
    remaining = list(ranked)
    selected: list[RerankCandidate] = []
    selected_ids: list[int] = []
    document_counts: dict[int, int] = {}
    used_tokens = 0

    while remaining and len(selected) < top_k:
        eligible = [
            item
            for item in remaining
            if document_counts.get(item.document_id, 0) < max_chunks_per_document
            and (not selected or used_tokens + item.token_count <= token_budget)
        ]
        if not eligible:
            break

        def mmr_score(item: RerankCandidate) -> tuple[float, float, int]:
            relevance = rerank_scores.get(item.chunk_id, 0.0)
            redundancy = max(
                (_content_similarity(item.content, chosen.content) for chosen in selected),
                default=0.0,
            )
            score = (mmr_lambda * relevance) - ((1.0 - mmr_lambda) * redundancy)
            return score, relevance, -item.chunk_id

        chosen = max(eligible, key=mmr_score)
        remaining.remove(chosen)
        selected.append(chosen)
        selected_ids.append(chosen.chunk_id)
        document_counts[chosen.document_id] = document_counts.get(chosen.document_id, 0) + 1
        used_tokens += chosen.token_count
    return selected_ids

