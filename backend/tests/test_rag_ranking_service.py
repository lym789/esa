from app.services.rag_ranking_service import (
    HeuristicReranker,
    RerankCandidate,
    reciprocal_rank_fusion,
    select_context_ids,
)


def candidate(chunk_id, document_id, content, dense, lexical, fusion, tokens=10):
    return RerankCandidate(
        chunk_id=chunk_id,
        document_id=document_id,
        content=content,
        token_count=tokens,
        dense_score=dense,
        lexical_score=lexical,
        fusion_score=fusion,
    )


def test_reciprocal_rank_fusion_rewards_multi_route_hits():
    scores = reciprocal_rank_fusion([1, 2], [2, 3], rrf_k=60)

    assert scores[2] > scores[1]
    assert scores[2] > scores[3]


def test_heuristic_reranker_combines_dense_lexical_and_fusion_scores():
    items = [
        candidate(1, 1, "semantic", 0.9, 0.0, 0.01),
        candidate(2, 2, "exact", 0.5, 1.0, 0.03),
    ]

    ranked = HeuristicReranker().rerank("query", items)

    assert [item.chunk_id for item in ranked] == [2, 1]


def test_context_selection_enforces_document_quota_budget_and_diversity():
    items = [
        candidate(1, 1, "VPN 登录统一认证", 0.9, 1.0, 0.03, tokens=20),
        candidate(2, 1, "VPN 登录统一认证说明", 0.8, 0.9, 0.02, tokens=20),
        candidate(3, 2, "网络连接排查步骤", 0.7, 0.5, 0.01, tokens=20),
    ]
    scores = {1: 0.9, 2: 0.8, 3: 0.7}

    selected = select_context_ids(
        items,
        scores,
        top_k=3,
        token_budget=40,
        max_chunks_per_document=1,
        mmr_lambda=0.75,
    )

    assert selected == [1, 3]
