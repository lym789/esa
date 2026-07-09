from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.approval import Approval
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.approval import ApprovalRead
from app.models.ticket_comment import TicketComment
from app.schemas.ticket import (
    TicketAssigneeUpdate,
    TicketCommentCreate,
    TicketCommentRead,
    TicketCreate,
    TicketDraftRead,
    TicketDraftRequest,
    TicketRead,
    TicketStatusUpdate,
)
from app.services.auth_service import get_user_by_id
from app.services.approval_service import create_ticket_approval
from app.services.ticket_service import (
    assign_ticket,
    create_ticket,
    create_ticket_comment,
    generate_ticket_draft,
    get_ticket_for_user,
    list_ticket_comments,
    list_tickets_for_user,
    update_ticket_status,
)
from app.services.trace_service import create_agent_trace


router = APIRouter()


def _approval_to_read(approval: Approval) -> ApprovalRead:
    return ApprovalRead(
        id=approval.id,
        status=approval.status,
        tool_name=approval.tool_name,
        tool_args=json.loads(approval.tool_args_json),
        requester_id=approval.requester_id,
        approver_id=approval.approver_id,
        decision_comment=approval.decision_comment,
        execution_result=json.loads(approval.execution_result_json),
        idempotency_key=approval.idempotency_key,
        created_at=approval.created_at,
        updated_at=approval.updated_at,
        decided_at=approval.decided_at,
    )


def _comment_to_read(db: Session, comment: TicketComment) -> TicketCommentRead:
    author = get_user_by_id(db, comment.author_id)
    return TicketCommentRead(
        id=comment.id,
        ticket_id=comment.ticket_id,
        author_id=comment.author_id,
        author_name=author.name if author is not None else f"用户 {comment.author_id}",
        author_role=author.role if author is not None else "unknown",
        content=comment.content,
        created_at=comment.created_at,
    )


@router.post("/draft", response_model=TicketDraftRead)
def create_ticket_draft(
    payload: TicketDraftRequest,
    current_user: User = Depends(get_current_user),
) -> TicketDraftRead:
    draft = generate_ticket_draft(payload.content)
    return TicketDraftRead(
        title=draft.title,
        description=draft.description,
        category=draft.category,
        priority=draft.priority,
        confidence=draft.confidence,
        reason=draft.reason,
    )


@router.post("", response_model=None)
def create_support_ticket(
    payload: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TicketRead | JSONResponse:
    if payload.priority == "urgent":
        approval = create_ticket_approval(
            db=db,
            requester=current_user,
            title=payload.title,
            description=payload.description,
            category=payload.category,
            priority=payload.priority,
            assignee_id=payload.assignee_id,
            source_conversation_id=payload.source_conversation_id,
        )
        create_agent_trace(
            db=db,
            user=current_user,
            conversation_id=payload.source_conversation_id,
            intent="create_ticket",
            user_input=payload.description,
            intent_data={
                "intent": "create_ticket",
                "confidence": 0.86,
                "need_ticket": True,
                "need_approval": True,
                "reason": "urgent 优先级工单需要审批",
            },
            tool_name="create_approval",
            tool_args={
                "title": payload.title,
                "description": payload.description,
                "category": payload.category,
                "priority": payload.priority,
                "assignee_id": payload.assignee_id,
                "source_conversation_id": payload.source_conversation_id,
            },
            approval_status="pending",
            final_result={"approval_id": approval.id, "status": approval.status},
        )
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=jsonable_encoder(
                {
                    "status": "pending_approval",
                    "approval": _approval_to_read(approval),
                }
            ),
        )

    ticket = create_ticket(
        db=db,
        requester=current_user,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        priority=payload.priority,
        assignee_id=payload.assignee_id,
        source_conversation_id=payload.source_conversation_id,
    )
    create_agent_trace(
        db=db,
        user=current_user,
        conversation_id=payload.source_conversation_id,
        intent="create_ticket",
        user_input=payload.description,
        intent_data={
            "intent": "create_ticket",
            "confidence": 0.86,
            "need_ticket": True,
            "need_approval": False,
            "reason": "普通工单直接创建",
        },
        tool_name="create_ticket",
        tool_args={
            "title": payload.title,
            "description": payload.description,
            "category": payload.category,
            "priority": payload.priority,
            "assignee_id": payload.assignee_id,
            "source_conversation_id": payload.source_conversation_id,
        },
        approval_status="not_required",
        final_result={"ticket_id": ticket.id, "ticket_no": ticket.ticket_no},
    )
    return TicketRead.model_validate(ticket)


@router.get("", response_model=list[TicketRead])
def list_support_tickets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Ticket]:
    return list_tickets_for_user(db, current_user)


@router.get("/{ticket_id}", response_model=TicketRead)
def get_support_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Ticket:
    ticket = get_ticket_for_user(db, ticket_id, current_user)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )
    return ticket


@router.patch("/{ticket_id}/status", response_model=TicketRead)
def update_support_ticket_status(
    ticket_id: int,
    payload: TicketStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Ticket:
    ticket = get_ticket_for_user(db, ticket_id, current_user)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )
    try:
        return update_ticket_status(db, ticket, current_user, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.patch("/{ticket_id}/assignee", response_model=TicketRead)
def assign_support_ticket(
    ticket_id: int,
    payload: TicketAssigneeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Ticket:
    ticket = get_ticket_for_user(db, ticket_id, current_user)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )
    assignee = get_user_by_id(db, payload.assignee_id) if payload.assignee_id is not None else None
    if payload.assignee_id is not None and assignee is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignee not found",
        )
    try:
        return assign_ticket(db, ticket, current_user, assignee)
    except ValueError as exc:
        status_code = status.HTTP_403_FORBIDDEN if "Only admins" in str(exc) else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.get("/{ticket_id}/comments", response_model=list[TicketCommentRead])
def list_support_ticket_comments(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TicketCommentRead]:
    ticket = get_ticket_for_user(db, ticket_id, current_user)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )
    return [_comment_to_read(db, comment) for comment in list_ticket_comments(db, ticket)]


@router.post("/{ticket_id}/comments", response_model=TicketCommentRead)
def create_support_ticket_comment(
    ticket_id: int,
    payload: TicketCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TicketCommentRead:
    ticket = get_ticket_for_user(db, ticket_id, current_user)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )
    comment = create_ticket_comment(db, ticket, current_user, payload.content)
    return _comment_to_read(db, comment)
