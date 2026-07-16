from __future__ import annotations

from app.services.rag_runtime import runtime_metrics
from app.services.resilience import resilience_registry


def _label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def render_prometheus_metrics() -> str:
    rag = runtime_metrics.snapshot()
    resilience = resilience_registry.snapshot()
    lines = [
        "# HELP rag_runtime_counter RAG runtime cumulative counter.",
        "# TYPE rag_runtime_counter counter",
    ]
    for name, value in sorted(rag["counters"].items()):
        lines.append(f'rag_runtime_counter{{name="{_label(name)}"}} {value}')
    lines.extend(
        [
            "# HELP rag_retrieval_cache_hit_ratio Retrieval cache hit ratio.",
            "# TYPE rag_retrieval_cache_hit_ratio gauge",
            f"rag_retrieval_cache_hit_ratio {rag['retrieval_cache_hit_rate']}",
            "# HELP rag_stage_latency_ms Observed RAG stage latency in milliseconds.",
            "# TYPE rag_stage_latency_ms gauge",
        ]
    )
    for stage, values in sorted(rag["stages"].items()):
        for quantile in ("p50", "p95", "p99"):
            lines.append(
                f'rag_stage_latency_ms{{stage="{_label(stage)}",quantile="{quantile}"}} '
                f"{values[f'{quantile}_ms']}"
            )
    lines.extend(
        [
            "# HELP rag_cache_stat RAG cache state and cumulative counters.",
            "# TYPE rag_cache_stat gauge",
        ]
    )
    for cache_name, stats in sorted(rag["caches"].items()):
        for stat, value in sorted(stats.items()):
            lines.append(
                f'rag_cache_stat{{cache="{_label(cache_name)}",stat="{_label(stat)}"}} {value}'
            )
    lines.extend(
        [
            "# HELP rag_component_stat External component reliability counters and gauges.",
            "# TYPE rag_component_stat gauge",
            "# HELP rag_component_circuit_state Current circuit state as a one-hot gauge.",
            "# TYPE rag_component_circuit_state gauge",
            "# HELP rag_component_errors_total External component errors by category.",
            "# TYPE rag_component_errors_total counter",
        ]
    )
    for component, snapshot in sorted(resilience.items()):
        escaped_component = _label(component)
        for state in ("closed", "open", "half_open"):
            value = 1 if snapshot["state"] == state else 0
            lines.append(
                f'rag_component_circuit_state{{component="{escaped_component}",state="{state}"}} {value}'
            )
        for stat, value in sorted(snapshot.items()):
            if stat in {"state", "error_categories"}:
                continue
            lines.append(
                f'rag_component_stat{{component="{escaped_component}",stat="{_label(stat)}"}} {value}'
            )
        for category, value in sorted(snapshot["error_categories"].items()):
            lines.append(
                f'rag_component_errors_total{{component="{escaped_component}",category="{_label(category)}"}} {value}'
            )
    return "\n".join(lines) + "\n"
