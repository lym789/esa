from app.core.config import Settings
from app.services.agent_intelligence_service import assess_risk, detect_intent
from app.services.llm_client import FakeLLMClient, LLMClientError


def test_detect_intent_uses_llm_when_configured():
    llm_client = FakeLLMClient(
        json_response={
            "intent": "create_ticket",
            "confidence": 0.91,
            "need_ticket": True,
            "need_approval": False,
            "reason": "用户明确要求创建邮箱无法登录工单。",
        }
    )
    settings = Settings(_env_file=None, llm_enabled=True, openai_api_key="sk-test")

    result = detect_intent("帮我创建一个邮箱无法登录工单", llm_client=llm_client, settings=settings)

    assert result.intent == "create_ticket"
    assert result.confidence == 0.91
    assert result.need_ticket is True
    assert result.need_approval is False
    assert "邮箱" in result.reason
    assert llm_client.calls[0]["mode"] == "json"
    assert "create_ticket" in llm_client.calls[0]["messages"][0]["content"]


def test_detect_intent_falls_back_to_knowledge_qa_when_llm_disabled_or_invalid():
    disabled = Settings(_env_file=None, llm_enabled=False, openai_api_key="sk-test")
    invalid_client = FakeLLMClient(
        json_response={
            "intent": "unsupported",
            "confidence": 0.99,
            "need_ticket": False,
            "need_approval": False,
            "reason": "invalid",
        }
    )
    enabled = Settings(_env_file=None, llm_enabled=True, openai_api_key="sk-test")

    disabled_result = detect_intent("VPN 怎么配置？", llm_client=invalid_client, settings=disabled)
    invalid_result = detect_intent("VPN 怎么配置？", llm_client=invalid_client, settings=enabled)

    assert disabled_result.intent == "knowledge_qa"
    assert disabled_result.confidence == 0.4
    assert invalid_result.intent == "knowledge_qa"
    assert invalid_result.confidence == 0.4


def test_assess_risk_uses_llm_when_configured():
    llm_client = FakeLLMClient(
        json_response={
            "risk_level": "high",
            "risk_reason": "请求涉及管理员权限变更。",
            "requires_approval": True,
        }
    )
    settings = Settings(_env_file=None, llm_enabled=True, openai_api_key="sk-test")

    result = assess_risk("请立刻给我管理员权限", llm_client=llm_client, settings=settings)

    assert result.risk_level == "high"
    assert result.requires_approval is True
    assert "管理员权限" in result.risk_reason
    assert "requires_approval" in llm_client.calls[0]["messages"][0]["content"]


def test_assess_risk_falls_back_to_low_when_llm_fails():
    llm_client = FakeLLMClient(error=LLMClientError("model unavailable"))
    settings = Settings(_env_file=None, llm_enabled=True, openai_api_key="sk-test")

    result = assess_risk("帮我创建一个普通工单", llm_client=llm_client, settings=settings)

    assert result.risk_level == "low"
    assert result.requires_approval is False
    assert "默认低风险" in result.risk_reason
