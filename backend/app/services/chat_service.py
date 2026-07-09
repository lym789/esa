from __future__ import annotations

import json
import re
from dataclasses import asdict
from time import perf_counter
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.services.agent_intelligence_service import IntentDetection, RiskAssessment, assess_risk, detect_intent
from app.services.embedding_client import EmbeddingClient
from app.services.llm_client import LLMClient, LLMClientError, build_llm_client, is_llm_configured
from app.services.prompt_templates import build_rag_answer_messages
from app.services.rag_service import SearchResult, format_citations, search
from app.services.ticket_service import TicketDraft, generate_ticket_draft
from app.services.trace_service import create_agent_trace, now_ms


REFUSAL_MESSAGE = "我没有在当前知识库中找到可靠依据，暂时不能确认这个问题。你可以换个问法，或创建工单让相关部门处理。"


def create_conversation(db: Session, user: User, title: str | None = None) -> Conversation:
    conversation = Conversation(title=title or "新的知识库问答", user_id=user.id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def list_conversations(db: Session, user: User) -> list[Conversation]:
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        .all()
    )


def get_conversation_for_user(db: Session, conversation_id: int, user: User) -> Conversation | None:
    return (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user.id)
        .first()
    )


def list_messages(db: Session, conversation: Conversation) -> list[Message]:
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.id.asc())
        .all()
    )


def _build_answer(content: str, results: list[SearchResult], citations: list[str]) -> str:
    if not results:
        return REFUSAL_MESSAGE

    top_result = results[0]
    answer = (
        "根据当前知识库，"
        f"{top_result.content.strip()}\n\n"
        "如果这个信息仍不能解决问题，建议创建工单让相关部门继续处理。"
    )
    return f"{answer}\n\n引用来源：\n" + "\n".join(citations)


def _citation_index(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        match = re.fullmatch(r"\[(\d+)\]|\d+", value.strip())
        if match:
            return int(match.group(1) or value.strip())
    return None


def _format_llm_answer(payload: dict[str, Any], citations: list[str]) -> tuple[str, list[str]]:
    answer = payload.get("answer")
    raw_citations = payload.get("citations")
    if not isinstance(answer, str) or not answer.strip():
        raise LLMClientError("LLM RAG response must include a non-empty answer")
    if not isinstance(raw_citations, list):
        raise LLMClientError("LLM RAG response must include citations")

    selected: list[str] = []
    for raw_citation in raw_citations:
        index = _citation_index(raw_citation)
        if index is None or index < 1 or index > len(citations):
            raise LLMClientError("LLM RAG response referenced an unknown citation")
        citation = citations[index - 1]
        if citation not in selected:
            selected.append(citation)

    if not selected:
        raise LLMClientError("LLM RAG response must cite at least one source")

    return f"{answer.strip()}\n\n引用来源：\n" + "\n".join(selected), selected


def _trace_chunk_payload(results: list[SearchResult]) -> list[dict[str, Any]]:
    return [
        {
            "citation": f"[{index}]",
            "chunk_id": result.chunk_id,
            "document_id": result.document_id,
            "document_name": result.document_name,
            "page": result.page,
            "section": result.section,
            "similarity": result.similarity,
            "content": result.content,
        }
        for index, result in enumerate(results, start=1)
    ]


def _build_llm_answer(
    content: str,
    results: list[SearchResult],
    citations: list[str],
    *,
    llm_client: LLMClient | None,
    settings: Settings,
) -> tuple[str, list[str], dict[str, Any]] | None:
    if not results or not is_llm_configured(settings):
        return None

    client = llm_client or build_llm_client(settings)
    response = client.generate_json(
        build_rag_answer_messages(
            question=content,
            retrieved_chunks=_trace_chunk_payload(results),
        )
    )
    answer, selected_citations = _format_llm_answer(response.data, citations)
    return answer, selected_citations, response.data


def _should_route_to_ticket(intent: IntentDetection) -> bool:
    return intent.intent == "create_ticket" and intent.need_ticket and intent.confidence >= 0.7


def _build_ticket_draft_answer(draft: TicketDraft, risk: RiskAssessment, requires_approval: bool) -> str:
    lines = [
        "我已根据你的描述整理出工单草稿：",
        f"标题：{draft.title}",
        f"分类：{draft.category}",
        f"优先级：{draft.priority}",
        f"描述：{draft.description}",
        f"判断理由：{draft.reason}",
        f"风险判断：{risk.risk_level}，{risk.risk_reason}",
    ]
    if requires_approval:
        lines.append("该请求可能需要审批，提交后会进入人工审批流程。")
    else:
        lines.append("请确认信息无误后，在工单页面提交。")
    return "\n".join(lines)


def _create_ticket_draft_message(
    *,
    db: Session,
    conversation: Conversation,
    content: str,
    intent: IntentDetection,
    risk: RiskAssessment,
    draft: TicketDraft,
    trace_start: float,
) -> Message:
    requires_approval = intent.need_approval or risk.requires_approval or draft.priority == "urgent"
    answer = _build_ticket_draft_answer(draft, risk, requires_approval)
    metadata = {
        "intent": asdict(intent),
        "risk": asdict(risk),
        "ticket_draft": asdict(draft),
        "requires_approval": requires_approval,
    }
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer,
        citations_json="[]",
        metadata_json=json.dumps(metadata, ensure_ascii=False),
    )
    db.add(assistant_message)
    db.add(conversation)
    db.commit()
    db.refresh(assistant_message)

    user = db.query(User).filter(User.id == conversation.user_id).one()
    create_agent_trace(
        db=db,
        user=user,
        conversation_id=conversation.id,
        intent="create_ticket",
        user_input=content,
        intent_data=asdict(intent),
        retrieved_chunks=[],
        llm_input_summary=f"intent={intent.intent}; confidence={intent.confidence}; risk={risk.risk_level}",
        llm_output=answer,
        tool_name="ticket_draft",
        tool_args={"content": content},
        approval_status="pending" if requires_approval else "not_required",
        final_result={
            "message_id": assistant_message.id,
            "ticket_draft": asdict(draft),
            "risk_level": risk.risk_level,
            "requires_approval": requires_approval,
        },
        elapsed_ms=now_ms(trace_start),
    )
    return assistant_message


def _serialize_results(results: list[SearchResult]) -> str:
    payload = [
        {
            "chunk_id": result.chunk_id,
            "document_id": result.document_id,
            "document_name": result.document_name,
            "page": result.page,
            "section": result.section,
            "similarity": result.similarity,
            "metadata": result.metadata,
        }
        for result in results
    ]
    return json.dumps({"results": payload}, ensure_ascii=False)


def _trace_chunks(results: list[SearchResult]) -> list[dict]:
    return [
        {
            "chunk_id": result.chunk_id,
            "document_id": result.document_id,
            "document_name": result.document_name,
            "page": result.page,
            "section": result.section,
            "similarity": result.similarity,
        }
        for result in results
    ]


def send_message(
    db: Session,
    conversation: Conversation,
    content: str,
    top_k: int,
    similarity_threshold: float,
    llm_client: LLMClient | None = None,
    embedding_client: EmbeddingClient | None = None,
    settings: Settings | None = None,
) -> Message:
    trace_start = perf_counter()
    active_settings = settings or get_settings()
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=content,
        citations_json="[]",
        metadata_json="{}",
    )
    db.add(user_message)
    db.commit()

    intent = detect_intent(content, llm_client=llm_client, settings=active_settings)
    if _should_route_to_ticket(intent):
        risk = assess_risk(content, llm_client=llm_client, settings=active_settings)
        draft = generate_ticket_draft(content, llm_client=llm_client, settings=active_settings)
        return _create_ticket_draft_message(
            db=db,
            conversation=conversation,
            content=content,
            intent=intent,
            risk=risk,
            draft=draft,
            trace_start=trace_start,
        )

    results = search(
        db=db,
        query=content,
        top_k=top_k,
        similarity_threshold=similarity_threshold,
        embedding_client=embedding_client,
        settings=active_settings,
    )
    citations = format_citations(results)
    llm_error: str | None = None
    llm_payload: dict[str, Any] | None = None
    llm_used = False
    selected_citations = citations
    try:
        llm_answer = _build_llm_answer(
            content,
            results,
            citations,
            llm_client=llm_client,
            settings=active_settings,
        )
    except LLMClientError as exc:
        llm_error = str(exc)
        llm_answer = None

    if llm_answer is None:
        answer = _build_answer(content, results, citations)
    else:
        answer, selected_citations, llm_payload = llm_answer
        llm_used = True

    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer,
        citations_json=json.dumps(selected_citations, ensure_ascii=False),
        metadata_json=_serialize_results(results),
    )
    db.add(assistant_message)
    db.add(conversation)
    db.commit()
    db.refresh(assistant_message)

    user = db.query(User).filter(User.id == conversation.user_id).one()
    create_agent_trace(
        db=db,
        user=user,
        conversation_id=conversation.id,
        intent="knowledge_qa",
        user_input=content,
        intent_data={
            "intent": "knowledge_qa",
            "confidence": 0.9 if results else 0.4,
            "need_ticket": False,
            "need_approval": False,
            "reason": "Chat 消息进入知识库问答流程",
        },
        retrieved_chunks=_trace_chunks(results),
        llm_input_summary=f"query={content}; top_k={top_k}; threshold={similarity_threshold}",
        llm_output=json.dumps(llm_payload, ensure_ascii=False) if llm_payload is not None else answer,
        tool_name="llm_rag_answer" if llm_used else "rag_search",
        tool_args={"query": content, "top_k": top_k, "similarity_threshold": similarity_threshold},
        approval_status="not_required",
        final_result={
            "message_id": assistant_message.id,
            "citations": selected_citations,
            "has_sources": bool(results),
            "llm_used": llm_used,
        },
        error_message=llm_error,
        elapsed_ms=now_ms(trace_start),
    )
    return assistant_message
