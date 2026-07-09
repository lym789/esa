from __future__ import annotations

import json
from time import perf_counter
from typing import Any

from sqlalchemy.orm import Session

from app.models.agent_trace import AgentTrace
from app.models.user import User


def now_ms(start: float) -> int:
    return max(0, int((perf_counter() - start) * 1000))


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def create_agent_trace(
    db: Session,
    user: User,
    intent: str,
    user_input: str,
    conversation_id: int | None = None,
    intent_data: dict[str, Any] | None = None,
    retrieved_chunks: list[dict[str, Any]] | None = None,
    llm_input_summary: str | None = None,
    llm_output: str | None = None,
    tool_name: str | None = None,
    tool_args: dict[str, Any] | None = None,
    approval_status: str = "not_required",
    final_result: dict[str, Any] | None = None,
    error_message: str | None = None,
    elapsed_ms: int = 0,
) -> AgentTrace:
    trace = AgentTrace(
        conversation_id=conversation_id,
        user_id=user.id,
        intent=intent,
        user_input=user_input,
        intent_json=_dumps(intent_data or {}),
        retrieved_chunks_json=_dumps(retrieved_chunks or []),
        llm_input_summary=llm_input_summary,
        llm_output=llm_output,
        tool_name=tool_name,
        tool_args_json=_dumps(tool_args or {}),
        approval_status=approval_status,
        final_result_json=_dumps(final_result or {}),
        error_message=error_message,
        elapsed_ms=elapsed_ms,
    )
    db.add(trace)
    db.commit()
    db.refresh(trace)
    return trace


def list_traces(db: Session) -> list[AgentTrace]:
    return db.query(AgentTrace).order_by(AgentTrace.created_at.desc(), AgentTrace.id.desc()).all()


def get_trace(db: Session, trace_id: int) -> AgentTrace | None:
    return db.query(AgentTrace).filter(AgentTrace.id == trace_id).first()


def list_traces_for_conversation(db: Session, conversation_id: int) -> list[AgentTrace]:
    return (
        db.query(AgentTrace)
        .filter(AgentTrace.conversation_id == conversation_id)
        .order_by(AgentTrace.created_at.desc(), AgentTrace.id.desc())
        .all()
    )
