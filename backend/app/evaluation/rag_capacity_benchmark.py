from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from math import ceil
from time import perf_counter

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models as _models  # noqa: F401 - register all SQLAlchemy tables
from app.core.config import Settings
from app.db.base import Base
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.user import User
from app.services.rag_runtime import reset_rag_runtime, runtime_metrics
from app.services.rag_service import embed_text, search_with_diagnostics


@dataclass(frozen=True)
class CapacityBenchmarkReport:
    document_count: int
    chunk_count: int
    query_count: int
    unique_query_count: int
    cache_hits: int
    cache_hit_rate: float
    cold_p95_ms: float
    warm_p95_ms: float
    total_elapsed_ms: float
    queries_per_second: float


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return round(ordered[max(0, ceil(len(ordered) * 0.95) - 1)], 3)


def run_capacity_benchmark(
    *,
    document_count: int = 500,
    query_count: int = 100,
    unique_query_count: int = 10,
) -> CapacityBenchmarkReport:
    if document_count < 1 or query_count < 1 or unique_query_count < 1:
        raise ValueError("benchmark counts must be positive")
    unique_query_count = min(unique_query_count, query_count)
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, future=True)
    db = session_factory()
    reset_rag_runtime()
    try:
        user = User(
            email="benchmark@example.com",
            name="Benchmark Admin",
            role="admin",
            hashed_password="not-used",
        )
        db.add(user)
        db.flush()
        for index in range(document_count):
            content = f"VPN 知识条目 {index}：统一身份认证、网络检查和错误码 ERR-{index:04d}。"
            document = Document(
                original_filename=f"BENCHMARK_{index}.md",
                stored_filename=f"benchmark-{index}.md",
                content_type="text/markdown",
                file_extension=".md",
                file_size=len(content.encode("utf-8")),
                storage_path=f"documents/benchmark-{index}.md",
                status="completed",
                chunk_count=1,
                uploaded_by_id=user.id,
            )
            db.add(document)
            db.flush()
            vector = embed_text(content)
            db.add(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=0,
                    content=content,
                    content_length=len(content),
                    metadata_json="{}",
                    embedding_json=json.dumps(vector),
                    embedding_model="local-hash-v1",
                    chunk_uid=f"benchmark-{index}",
                )
            )
        db.commit()

        settings = Settings(
            _env_file=None,
            rag_cache_enabled=True,
            rag_cache_ttl_seconds=300,
            rag_cache_max_entries=max(10, unique_query_count * 2),
            rag_candidate_k=30,
        )
        cold_samples: list[float] = []
        warm_samples: list[float] = []
        started = perf_counter()
        for index in range(query_count):
            query_index = index % unique_query_count
            execution = search_with_diagnostics(
                db,
                f"VPN ERR-{query_index:04d}",
                top_k=5,
                similarity_threshold=0.0,
                user=user,
                settings=settings,
            )
            elapsed = execution.diagnostics.timings_ms["total"]
            (warm_samples if execution.diagnostics.cache_hit else cold_samples).append(elapsed)
        total_elapsed_ms = (perf_counter() - started) * 1000
        snapshot = runtime_metrics.snapshot()
        cache_hits = snapshot["counters"].get("retrieval_cache_hits", 0)
        return CapacityBenchmarkReport(
            document_count=document_count,
            chunk_count=document_count,
            query_count=query_count,
            unique_query_count=unique_query_count,
            cache_hits=cache_hits,
            cache_hit_rate=round(cache_hits / query_count, 4),
            cold_p95_ms=_p95(cold_samples),
            warm_p95_ms=_p95(warm_samples),
            total_elapsed_ms=round(total_elapsed_ms, 3),
            queries_per_second=round(query_count / (total_elapsed_ms / 1000), 2),
        )
    finally:
        db.close()
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a repeatable local RAG capacity benchmark")
    parser.add_argument("--documents", type=int, default=500)
    parser.add_argument("--queries", type=int, default=100)
    parser.add_argument("--unique-queries", type=int, default=10)
    args = parser.parse_args()
    report = run_capacity_benchmark(
        document_count=args.documents,
        query_count=args.queries,
        unique_query_count=args.unique_queries,
    )
    print(json.dumps(asdict(report), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
