from __future__ import annotations

from collections import OrderedDict, defaultdict, deque
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from math import ceil
from threading import RLock
from time import monotonic
from typing import Any, Hashable

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.rag_index_state import RAGIndexState


@dataclass(frozen=True)
class SearchDiagnostics:
    cache_hit: bool = False
    dense_candidates: int = 0
    lexical_candidates: int = 0
    selected_count: int = 0
    filtered_injection_count: int = 0
    degraded_components: tuple[str, ...] = ()
    timings_ms: dict[str, float] = field(default_factory=dict)


class BoundedTTLCache:
    def __init__(self) -> None:
        self._items: OrderedDict[Hashable, tuple[float, Any]] = OrderedDict()
        self._lock = RLock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._invalidations = 0

    def get(self, key: Hashable) -> Any | None:
        now = monotonic()
        with self._lock:
            item = self._items.get(key)
            if item is None:
                self._misses += 1
                return None
            expires_at, value = item
            if expires_at <= now:
                self._items.pop(key, None)
                self._misses += 1
                return None
            self._items.move_to_end(key)
            self._hits += 1
            return deepcopy(value)

    def set(self, key: Hashable, value: Any, *, ttl_seconds: int, max_entries: int) -> None:
        with self._lock:
            self._items[key] = (monotonic() + ttl_seconds, deepcopy(value))
            self._items.move_to_end(key)
            while len(self._items) > max_entries:
                self._items.popitem(last=False)
                self._evictions += 1

    def invalidate(self) -> None:
        with self._lock:
            self._items.clear()
            self._invalidations += 1

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return {
                "entries": len(self._items),
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "invalidations": self._invalidations,
            }

    def reset(self) -> None:
        with self._lock:
            self._items.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0
            self._invalidations = 0


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, ceil(percentile * len(ordered)) - 1)
    return round(ordered[index], 3)


class RAGRuntimeMetrics:
    def __init__(self) -> None:
        self._lock = RLock()
        self._counters: dict[str, int] = defaultdict(int)
        self._stage_samples: dict[str, deque[float]] = defaultdict(deque)

    def observe(self, diagnostics: SearchDiagnostics, *, max_samples: int) -> None:
        with self._lock:
            self._counters["searches"] += 1
            if diagnostics.cache_hit:
                self._counters["retrieval_cache_hits"] += 1
            self._counters["selected_chunks"] += diagnostics.selected_count
            self._counters["filtered_injection_chunks"] += diagnostics.filtered_injection_count
            for component in diagnostics.degraded_components:
                self._counters[f"degraded_{component}"] += 1
            for stage, elapsed_ms in diagnostics.timings_ms.items():
                samples = self._stage_samples[stage]
                samples.append(float(elapsed_ms))
                while len(samples) > max_samples:
                    samples.popleft()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            counters = dict(self._counters)
            searches = counters.get("searches", 0)
            hits = counters.get("retrieval_cache_hits", 0)
            stages = {
                stage: {
                    "samples": len(values),
                    "p50_ms": _percentile(list(values), 0.50),
                    "p95_ms": _percentile(list(values), 0.95),
                    "p99_ms": _percentile(list(values), 0.99),
                    "max_ms": round(max(values), 3) if values else 0.0,
                }
                for stage, values in self._stage_samples.items()
            }
        return {
            "counters": counters,
            "retrieval_cache_hit_rate": round(hits / searches, 4) if searches else 0.0,
            "stages": stages,
            "caches": {
                "retrieval": retrieval_cache.snapshot(),
                "query_embedding": query_embedding_cache.snapshot(),
            },
        }

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._stage_samples.clear()


retrieval_cache = BoundedTTLCache()
query_embedding_cache = BoundedTTLCache()
runtime_metrics = RAGRuntimeMetrics()


def invalidate_rag_caches() -> None:
    retrieval_cache.invalidate()


def get_rag_revision(db: Session) -> int:
    revision = (
        db.query(RAGIndexState.revision).filter(RAGIndexState.id == 1).scalar()
    )
    return int(revision or 0)


def bump_rag_revision(db: Session) -> int:
    result = db.execute(
        update(RAGIndexState)
        .where(RAGIndexState.id == 1)
        .values(revision=RAGIndexState.revision + 1)
    )
    if result.rowcount == 0:
        db.add(RAGIndexState(id=1, revision=1))
        revision = 1
    else:
        db.flush()
        revision = get_rag_revision(db)
    invalidate_rag_caches()
    return revision


def reset_rag_runtime() -> None:
    retrieval_cache.reset()
    query_embedding_cache.reset()
    runtime_metrics.reset()


def diagnostics_payload(diagnostics: SearchDiagnostics) -> dict[str, Any]:
    return asdict(diagnostics)
