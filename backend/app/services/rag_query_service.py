from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Sequence


FOLLOW_UP_MARKERS = {
    "这个",
    "那个",
    "上述",
    "刚才",
    "它",
    "该流程",
    "该政策",
    "还需要",
    "然后呢",
}


@dataclass(frozen=True)
class QueryPlan:
    original_query: str
    normalized_query: str
    retrieval_query: str
    rewritten: bool
    rewrite_reason: str | None = None


def normalize_query(query: str) -> str:
    normalized = unicodedata.normalize("NFKC", query)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _looks_like_follow_up(query: str) -> bool:
    return len(query) <= 6 or any(marker in query for marker in FOLLOW_UP_MARKERS)


def build_query_plan(query: str, previous_user_messages: Sequence[str] = ()) -> QueryPlan:
    normalized = normalize_query(query)
    previous = next(
        (normalize_query(message) for message in reversed(previous_user_messages) if normalize_query(message)),
        None,
    )
    if previous and _looks_like_follow_up(normalized):
        return QueryPlan(
            original_query=query,
            normalized_query=normalized,
            retrieval_query=f"{previous}；追问：{normalized}",
            rewritten=True,
            rewrite_reason="短问题或指代词需要补充上一轮用户问题",
        )
    return QueryPlan(
        original_query=query,
        normalized_query=normalized,
        retrieval_query=normalized,
        rewritten=False,
    )
