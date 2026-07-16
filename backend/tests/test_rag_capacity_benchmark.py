from app.evaluation.rag_capacity_benchmark import run_capacity_benchmark


def test_capacity_benchmark_reports_cold_and_warm_cache_performance():
    report = run_capacity_benchmark(document_count=12, query_count=6, unique_query_count=2)

    assert report.document_count == 12
    assert report.chunk_count == 12
    assert report.cache_hits == 4
    assert report.cache_hit_rate == 0.6667
    assert report.cold_p95_ms > 0
    assert report.warm_p95_ms >= 0
    assert report.queries_per_second > 0
