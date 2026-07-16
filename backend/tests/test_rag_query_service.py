from app.services.rag_query_service import build_query_plan, normalize_query


def test_normalize_query_handles_width_case_and_whitespace():
    assert normalize_query("  ＶＰＮ   Login  ") == "VPN Login"


def test_build_query_plan_rewrites_follow_up_with_previous_question():
    plan = build_query_plan(
        "这个需要审批吗？",
        ["VPN 怎么配置？", "差旅报销需要哪些凭证？"],
    )

    assert plan.rewritten is True
    assert "差旅报销需要哪些凭证" in plan.retrieval_query
    assert "这个需要审批吗" in plan.retrieval_query


def test_build_query_plan_keeps_standalone_question():
    plan = build_query_plan(
        "公司 VPN 登录失败时应该如何排查网络和统一身份认证？",
        ["年假怎么申请？"],
    )

    assert plan.rewritten is False
    assert plan.retrieval_query == plan.normalized_query


def test_build_query_plan_does_not_rewrite_short_but_specific_new_topic():
    plan = build_query_plan("年假怎么申请？", ["VPN 怎么登录？"])

    assert plan.rewritten is False
