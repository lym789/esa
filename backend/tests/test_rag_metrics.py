import json

import pytest

from app.evaluation.rag_evaluator import load_cases
from app.evaluation.rag_metrics import aggregate_rankings, evaluate_ranking


def test_evaluate_ranking_calculates_recall_rr_and_ndcg():
    metrics = evaluate_ranking(
        ["unrelated.md", "policy-a.md", "policy-b.md"],
        ["policy-a.md", "policy-b.md"],
        k=3,
    )

    assert metrics.recall_at_k == 1.0
    assert metrics.reciprocal_rank == 0.5
    assert 0.69 < metrics.ndcg_at_k < 0.70


def test_evaluate_ranking_deduplicates_retrieved_documents():
    metrics = evaluate_ranking(["policy.md", "policy.md"], ["policy.md"], k=2)

    assert metrics.recall_at_k == 1.0
    assert metrics.reciprocal_rank == 1.0
    assert metrics.ndcg_at_k == 1.0


def test_aggregate_rankings_handles_empty_and_multiple_cases():
    assert aggregate_rankings([]).case_count == 0
    first = evaluate_ranking(["a"], ["a"], k=1)
    second = evaluate_ranking(["x"], ["a"], k=1)

    aggregate = aggregate_rankings([first, second])

    assert aggregate.case_count == 2
    assert aggregate.recall_at_k == 0.5
    assert aggregate.mean_reciprocal_rank == 0.5
    assert aggregate.ndcg_at_k == 0.5


def test_load_cases_validates_jsonl(tmp_path):
    dataset = tmp_path / "golden.jsonl"
    dataset.write_text(
        json.dumps(
            {
                "case_id": "vpn",
                "query": "VPN 怎么登录？",
                "relevant_documents": ["IT_VPN_FAQ.md"],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    cases = load_cases(dataset)

    assert cases[0].case_id == "vpn"
    assert cases[0].relevant_documents == ["IT_VPN_FAQ.md"]


def test_evaluate_ranking_rejects_invalid_inputs():
    with pytest.raises(ValueError, match="k"):
        evaluate_ranking(["a"], ["a"], k=0)
    with pytest.raises(ValueError, match="relevant"):
        evaluate_ranking(["a"], [], k=1)
