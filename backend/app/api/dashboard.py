from collections import Counter

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import get_settings
from app.models.approval import Approval
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.dashboard import (
    DashboardAnalyticsRead,
    DashboardIntegrationRead,
    DashboardNotificationRead,
    DashboardOverviewRead,
    DashboardSearchResponse,
    DashboardSearchResultRead,
    DashboardStatRead,
    DashboardStatusRead,
)
from app.services.approval_service import list_approvals_for_user
from app.services.embedding_client import is_embedding_configured
from app.services.llm_client import is_llm_configured
from app.services.rag_service import current_document_chunk_condition, document_access_conditions
from app.services.ticket_service import list_tickets_for_user


router = APIRouter()
settings = get_settings()


def _ticket_query_for_user(db: Session, user: User):
    query = db.query(Ticket)
    if user.role == "admin":
        return query
    if user.role == "handler":
        return query.filter(Ticket.assignee_id == user.id)
    return query.filter(Ticket.requester_id == user.id)


def _average_resolution_hours(tickets: list[Ticket]) -> float:
    durations = [
        (ticket.updated_at - ticket.created_at).total_seconds() / 3600
        for ticket in tickets
        if ticket.status in {"resolved", "closed"} and ticket.updated_at and ticket.created_at
    ]
    return round(sum(durations) / len(durations), 1) if durations else 0.0


def _notifications(db: Session, user: User, tickets: list[Ticket]) -> list[DashboardNotificationRead]:
    items: list[DashboardNotificationRead] = []
    for approval in list_approvals_for_user(db, user):
        if approval.status != "pending":
            continue
        items.append(
            DashboardNotificationRead(
                id=f"approval-{approval.id}",
                kind="approval",
                title="待处理审批",
                message="有一项请求正在等待审批处理。",
                href=f"/approvals?approval={approval.id}",
                created_at=approval.created_at,
            )
        )
    for ticket in tickets:
        if ticket.status not in {"open", "in_progress"}:
            continue
        items.append(
            DashboardNotificationRead(
                id=f"ticket-{ticket.id}",
                kind="ticket",
                title="待处理工单",
                message=f"{ticket.ticket_no} · {ticket.title}",
                href=f"/tickets/{ticket.id}",
                created_at=ticket.updated_at,
            )
        )
    return sorted(items, key=lambda item: item.created_at, reverse=True)[:8]


@router.get("/overview", response_model=DashboardOverviewRead)
def dashboard_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardOverviewRead:
    tickets = list_tickets_for_user(db, current_user)
    status_counts = Counter(ticket.status for ticket in tickets)
    priority_counts = Counter(ticket.priority for ticket in tickets)
    category_counts = Counter(ticket.category for ticket in tickets)
    knowledge_articles = db.query(Document).filter(Document.status == "completed").count()
    open_count = status_counts["open"] + status_counts["in_progress"]
    resolved_count = status_counts["resolved"] + status_counts["closed"]
    average_hours = _average_resolution_hours(tickets)
    llm_configured = is_llm_configured(settings)
    embedding_configured = is_embedding_configured(settings)

    return DashboardOverviewRead(
        stats=[
            DashboardStatRead(
                key="knowledge_articles",
                label="知识文章",
                value=knowledge_articles,
                detail="已完成解析的知识文档",
            ),
            DashboardStatRead(
                key="open_tickets",
                label="待处理工单",
                value=open_count,
                detail="当前账号可见的待处理工单",
            ),
            DashboardStatRead(
                key="resolved_tickets",
                label="已解决工单",
                value=resolved_count,
                detail="当前账号可见的已完成工单",
            ),
            DashboardStatRead(
                key="average_resolution_hours",
                label="平均解决时长",
                value=average_hours,
                detail="根据已解决工单实时计算",
            ),
        ],
        status=DashboardStatusRead(
            backend="online",
            database="online",
            llm_configured=llm_configured,
            embedding_configured=embedding_configured,
        ),
        notifications=_notifications(db, current_user, tickets),
        analytics=DashboardAnalyticsRead(
            ticket_status=dict(status_counts),
            ticket_priority=dict(priority_counts),
            ticket_category=dict(category_counts),
        ),
        integrations=[
            DashboardIntegrationRead(
                key="database",
                name="数据库与向量检索",
                status="connected",
                detail="业务数据和知识向量存储可用",
            ),
            DashboardIntegrationRead(
                key="llm",
                name="大模型服务",
                status="configured" if llm_configured else "disabled",
                detail=settings.llm_model if llm_configured else "尚未启用或配置不完整",
            ),
            DashboardIntegrationRead(
                key="embedding",
                name="Embedding 服务",
                status="configured" if embedding_configured else "disabled",
                detail=settings.embedding_model if embedding_configured else "使用本地检索或尚未配置",
            ),
            DashboardIntegrationRead(
                key="agent_trace",
                name="智能体追踪",
                status="active",
                detail="问答、工具调用和审批链路已启用审计记录",
            ),
        ],
    )


@router.get("/search", response_model=DashboardSearchResponse)
def dashboard_search(
    q: str = Query(min_length=1, max_length=120),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardSearchResponse:
    query = q.strip()
    pattern = f"%{query}%"
    results: list[DashboardSearchResultRead] = []

    chunks = (
        db.query(DocumentChunk, Document)
        .join(Document, DocumentChunk.document_id == Document.id)
        .filter(
            *document_access_conditions(user=current_user),
            current_document_chunk_condition(),
            DocumentChunk.content.ilike(pattern),
        )
        .order_by(DocumentChunk.id.desc())
        .limit(5)
        .all()
    )
    for chunk, document in chunks:
        results.append(
            DashboardSearchResultRead(
                kind="knowledge",
                title=chunk.section or document.original_filename,
                snippet=chunk.content[:180],
                href="/chat",
            )
        )

    documents = (
        db.query(Document)
        .filter(
            *document_access_conditions(user=current_user),
            Document.original_filename.ilike(pattern),
        )
        .order_by(Document.updated_at.desc(), Document.id.desc())
        .limit(5)
        .all()
    )
    for document in documents:
        results.append(
            DashboardSearchResultRead(
                kind="document",
                title=document.original_filename,
                snippet=f"状态：{document.status} · {document.chunk_count} 个知识片段",
                href=f"/admin/documents?document={document.id}",
            )
        )

    tickets = (
        _ticket_query_for_user(db, current_user)
        .filter(
            or_(
                Ticket.ticket_no.ilike(pattern),
                Ticket.title.ilike(pattern),
                Ticket.description.ilike(pattern),
                Ticket.category.ilike(pattern),
            )
        )
        .order_by(Ticket.updated_at.desc(), Ticket.id.desc())
        .limit(5)
        .all()
    )
    for ticket in tickets:
        results.append(
            DashboardSearchResultRead(
                kind="ticket",
                title=f"{ticket.ticket_no} · {ticket.title}",
                snippet=ticket.description[:180],
                href=f"/tickets/{ticket.id}",
            )
        )

    return DashboardSearchResponse(query=query, results=results[:12])
