from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.ticket import Ticket
from app.models.ticket_comment import TicketComment
from app.models.user import User
from app.services.llm_client import LLMClient, LLMClientError, build_llm_client, is_llm_configured
from app.services.prompt_templates import build_ticket_draft_messages


ALLOWED_TICKET_STATUSES = {"open", "in_progress", "resolved", "closed"}
ALLOWED_TICKET_CATEGORIES = {"IT", "HR", "Finance", "Admin", "Other"}
ALLOWED_TICKET_PRIORITIES = {"low", "medium", "high", "urgent"}


@dataclass(frozen=True)
class TicketDraft:
    title: str
    description: str
    category: str
    priority: str
    confidence: float
    reason: str


def _normalize_content(content: str) -> str:
    return " ".join(content.strip().split())


def _infer_category(content: str) -> str:
    lowered = content.lower()
    if any(keyword in lowered for keyword in ["it", "vpn", "邮箱", "邮件", "登录", "电脑", "网络", "系统", "账号"]):
        return "IT"
    if any(keyword in lowered for keyword in ["hr", "请假", "年假", "入职", "离职", "社保", "薪资"]):
        return "HR"
    if any(keyword in lowered for keyword in ["finance", "报销", "发票", "付款", "预算", "财务"]):
        return "Finance"
    if any(keyword in lowered for keyword in ["门禁", "工位", "会议室", "办公用品", "行政"]):
        return "Admin"
    return "Other"


def _infer_priority(content: str) -> str:
    lowered = content.lower()
    if any(keyword in lowered for keyword in ["urgent", "紧急", "完全无法", "中断", "立刻", "马上"]):
        return "urgent"
    if any(keyword in lowered for keyword in ["高优先级", "严重", "无法工作", "影响工作"]):
        return "high"
    if any(keyword in lowered for keyword in ["低优先级", "不着急", "有空"]):
        return "low"
    return "medium"


def _strip_ticket_words(content: str) -> str:
    result = content
    for pattern in [
        r"帮我",
        r"请帮我",
        r"创建一个?",
        r"提交一个?",
        r"新建一个?",
        r"工单",
        r"ticket",
        r"紧急",
        r"urgent",
        r"\bIT\b",
    ]:
        result = re.sub(pattern, "", result, flags=re.IGNORECASE)
    return _normalize_content(result).strip("，。,. ")


def _build_title(content: str, category: str) -> str:
    cleaned = _strip_ticket_words(content)
    if not cleaned:
        return f"{category} 支持请求"

    if len(cleaned) <= 32:
        return cleaned
    return cleaned[:32].rstrip() + "..."


def _local_ticket_draft(normalized: str) -> TicketDraft:
    category = _infer_category(normalized)
    priority = _infer_priority(normalized)
    title = _build_title(normalized, category)
    confidence = 0.86 if category != "Other" else 0.62
    reason = "根据用户描述中的关键词生成工单草稿"
    return TicketDraft(
        title=title,
        description=normalized,
        category=category,
        priority=priority,
        confidence=confidence,
        reason=reason,
    )


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise LLMClientError(f"LLM ticket draft response must include {key}")
    return _normalize_content(value)


def _draft_from_llm_payload(payload: dict[str, Any]) -> TicketDraft:
    title = _required_string(payload, "title")[:255]
    description = _required_string(payload, "description")
    category = _required_string(payload, "category")
    priority = _required_string(payload, "priority")
    reason = _required_string(payload, "reason")
    confidence = payload.get("confidence")

    if category not in ALLOWED_TICKET_CATEGORIES:
        raise LLMClientError("LLM ticket draft response used an unsupported category")
    if priority not in ALLOWED_TICKET_PRIORITIES:
        raise LLMClientError("LLM ticket draft response used an unsupported priority")
    if not isinstance(confidence, (int, float)):
        raise LLMClientError("LLM ticket draft response must include numeric confidence")

    return TicketDraft(
        title=title,
        description=description,
        category=category,
        priority=priority,
        confidence=max(0.0, min(1.0, float(confidence))),
        reason=reason,
    )


def _llm_ticket_draft(
    normalized: str,
    *,
    llm_client: LLMClient | None,
    settings: Settings,
) -> TicketDraft | None:
    if not is_llm_configured(settings):
        return None

    client = llm_client or build_llm_client(settings)
    response = client.generate_json(build_ticket_draft_messages(normalized))
    return _draft_from_llm_payload(response.data)


def generate_ticket_draft(
    content: str,
    llm_client: LLMClient | None = None,
    settings: Settings | None = None,
) -> TicketDraft:
    normalized = _normalize_content(content)
    active_settings = settings or get_settings()
    try:
        draft = _llm_ticket_draft(normalized, llm_client=llm_client, settings=active_settings)
    except LLMClientError:
        draft = None
    return draft or _local_ticket_draft(normalized)


def _next_ticket_no(db: Session) -> str:
    date_part = datetime.now().strftime("%Y%m%d")
    prefix = f"TKT-{date_part}-"
    count = db.query(Ticket).filter(Ticket.ticket_no.like(f"{prefix}%")).count()
    return f"{prefix}{count + 1:04d}"


def create_ticket(
    db: Session,
    requester: User,
    title: str,
    description: str,
    category: str,
    priority: str,
    assignee_id: int | None = None,
    source_conversation_id: int | None = None,
) -> Ticket:
    ticket = Ticket(
        ticket_no=_next_ticket_no(db),
        title=title.strip(),
        description=description.strip(),
        category=category,
        priority=priority,
        status="open",
        requester_id=requester.id,
        assignee_id=assignee_id,
        source_conversation_id=source_conversation_id,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def list_tickets_for_user(db: Session, user: User) -> list[Ticket]:
    query = db.query(Ticket)
    if user.role == "admin":
        pass
    elif user.role == "handler":
        query = query.filter(Ticket.assignee_id == user.id)
    else:
        query = query.filter(Ticket.requester_id == user.id)
    return query.order_by(Ticket.created_at.desc(), Ticket.id.desc()).all()


def get_ticket_for_user(db: Session, ticket_id: int, user: User) -> Ticket | None:
    query = db.query(Ticket).filter(Ticket.id == ticket_id)
    if user.role == "admin":
        return query.first()
    if user.role == "handler":
        return query.filter(Ticket.assignee_id == user.id).first()
    return query.filter(Ticket.requester_id == user.id).first()


def update_ticket_status(db: Session, ticket: Ticket, actor: User, status: str) -> Ticket:
    if status not in ALLOWED_TICKET_STATUSES:
        raise ValueError("Unsupported ticket status")
    if actor.role not in {"handler", "admin"}:
        raise ValueError("Only handlers or admins can update ticket status")
    if actor.role == "handler" and ticket.assignee_id != actor.id:
        raise ValueError("Only assigned handlers can update ticket status")

    ticket.status = status
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def assign_ticket(db: Session, ticket: Ticket, actor: User, assignee: User | None) -> Ticket:
    if actor.role != "admin":
        raise ValueError("Only admins can assign tickets")
    if assignee is not None and assignee.role != "handler":
        raise ValueError("Ticket assignee must be a handler")
    if assignee is not None and not assignee.is_active:
        raise ValueError("Ticket assignee must be active")

    ticket.assignee_id = assignee.id if assignee is not None else None
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def create_ticket_comment(db: Session, ticket: Ticket, author: User, content: str) -> TicketComment:
    comment = TicketComment(
        ticket_id=ticket.id,
        author_id=author.id,
        content=content.strip(),
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def list_ticket_comments(db: Session, ticket: Ticket) -> list[TicketComment]:
    return (
        db.query(TicketComment)
        .filter(TicketComment.ticket_id == ticket.id)
        .order_by(TicketComment.created_at.asc(), TicketComment.id.asc())
        .all()
    )
