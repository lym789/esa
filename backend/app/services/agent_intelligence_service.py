from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import Settings, get_settings
from app.services.llm_client import LLMClient, LLMClientError, build_llm_client, is_llm_configured
from app.services.prompt_templates import build_intent_detection_messages, build_risk_assessment_messages


ALLOWED_INTENTS = {"knowledge_qa", "create_ticket", "ticket_query", "approval_query", "unknown"}
ALLOWED_RISK_LEVELS = {"low", "medium", "high"}


@dataclass(frozen=True)
class IntentDetection:
    intent: str
    confidence: float
    need_ticket: bool
    need_approval: bool
    reason: str


@dataclass(frozen=True)
class RiskAssessment:
    risk_level: str
    risk_reason: str
    requires_approval: bool


def _fallback_intent() -> IntentDetection:
    return IntentDetection(
        intent="knowledge_qa",
        confidence=0.4,
        need_ticket=False,
        need_approval=False,
        reason="模型未启用或输出不可用，保守进入知识库问答流程",
    )


def _fallback_risk() -> RiskAssessment:
    return RiskAssessment(
        risk_level="low",
        risk_reason="模型未启用或输出不可用，默认低风险并保留后端硬规则",
        requires_approval=False,
    )


def _bool_value(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise LLMClientError(f"Intent response must include boolean {key}")
    return value


def _confidence(payload: dict[str, Any]) -> float:
    value = payload.get("confidence")
    if not isinstance(value, (int, float)):
        raise LLMClientError("Intent response must include numeric confidence")
    return max(0.0, min(1.0, float(value)))


def _string_value(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise LLMClientError(f"Model response must include non-empty {key}")
    return value.strip()


def _intent_from_payload(payload: dict[str, Any]) -> IntentDetection:
    intent = _string_value(payload, "intent")
    if intent not in ALLOWED_INTENTS:
        raise LLMClientError("Intent response used an unsupported intent")
    return IntentDetection(
        intent=intent,
        confidence=_confidence(payload),
        need_ticket=_bool_value(payload, "need_ticket"),
        need_approval=_bool_value(payload, "need_approval"),
        reason=_string_value(payload, "reason"),
    )


def _risk_from_payload(payload: dict[str, Any]) -> RiskAssessment:
    risk_level = _string_value(payload, "risk_level")
    if risk_level not in ALLOWED_RISK_LEVELS:
        raise LLMClientError("Risk response used an unsupported risk level")
    requires_approval = payload.get("requires_approval")
    if not isinstance(requires_approval, bool):
        raise LLMClientError("Risk response must include boolean requires_approval")
    return RiskAssessment(
        risk_level=risk_level,
        risk_reason=_string_value(payload, "risk_reason"),
        requires_approval=requires_approval,
    )


def detect_intent(
    content: str,
    *,
    llm_client: LLMClient | None = None,
    settings: Settings | None = None,
) -> IntentDetection:
    active_settings = settings or get_settings()
    if not is_llm_configured(active_settings):
        return _fallback_intent()

    try:
        client = llm_client or build_llm_client(active_settings)
        response = client.generate_json(build_intent_detection_messages(content))
        return _intent_from_payload(response.data)
    except LLMClientError:
        return _fallback_intent()


def assess_risk(
    content: str,
    *,
    llm_client: LLMClient | None = None,
    settings: Settings | None = None,
) -> RiskAssessment:
    active_settings = settings or get_settings()
    if not is_llm_configured(active_settings):
        return _fallback_risk()

    try:
        client = llm_client or build_llm_client(active_settings)
        response = client.generate_json(build_risk_assessment_messages(content))
        return _risk_from_payload(response.data)
    except LLMClientError:
        return _fallback_risk()
