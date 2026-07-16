from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean
from typing import Sequence


@dataclass(frozen=True)
class RankingMetrics:
    recall_at_k: float
    reciprocal_rank: float
    ndcg_at_k: float


@dataclass(frozen=True)
class AggregateRankingMetrics:
    case_count: int
    recall_at_k: float
    mean_reciprocal_rank: float
    ndcg_at_k: float


def _unique(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(values))


def evaluate_ranking(
    retrieved: Sequence[str],
    relevant: Sequence[str],
    *,
    k: int,
) -> RankingMetrics:
    if k <= 0:
        raise ValueError("k must be greater than 0")

    relevant_set = set(relevant)
    if not relevant_set:
        raise ValueError("relevant must contain at least one item")

    ranked = _unique(retrieved)[:k]
    hits = [1 if item in relevant_set else 0 for item in ranked]
    recall = len({item for item in ranked if item in relevant_set}) / len(relevant_set)

    first_relevant_rank = next((index for index, hit in enumerate(hits, start=1) if hit), None)
    reciprocal_rank = 0.0 if first_relevant_rank is None else 1.0 / first_relevant_rank

    dcg = sum(hit / math.log2(index + 1) for index, hit in enumerate(hits, start=1))
    ideal_hits = [1] * min(len(relevant_set), k)
    ideal_dcg = sum(hit / math.log2(index + 1) for index, hit in enumerate(ideal_hits, start=1))
    ndcg = dcg / ideal_dcg if ideal_dcg else 0.0

    return RankingMetrics(
        recall_at_k=recall,
        reciprocal_rank=reciprocal_rank,
        ndcg_at_k=ndcg,
    )


def aggregate_rankings(metrics: Sequence[RankingMetrics]) -> AggregateRankingMetrics:
    if not metrics:
        return AggregateRankingMetrics(
            case_count=0,
            recall_at_k=0.0,
            mean_reciprocal_rank=0.0,
            ndcg_at_k=0.0,
        )
    return AggregateRankingMetrics(
        case_count=len(metrics),
        recall_at_k=mean(item.recall_at_k for item in metrics),
        mean_reciprocal_rank=mean(item.reciprocal_rank for item in metrics),
        ndcg_at_k=mean(item.ndcg_at_k for item in metrics),
    )

