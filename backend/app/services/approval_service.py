from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.approval import Approval
from app.models.ticket import Ticket
from app.models.user import User
from app.services.ticket_service import create_ticket


def create_ticket_approval(
    db: Session,
    requester: User,
    title: str,
    description: str,
    category: str,
    priority: str,
    assignee_id: int | None = None,
    source_conversation_id: int | None = None,
) -> Approval:
    tool_args = {
        "requester_id": requester.id,
        "title": title.strip(),
        "description": description.strip(),
        "category": category,
        "priority": priority,
        "assignee_id": assignee_id,
        "source_conversation_id": source_conversation_id,
    }
    approval = Approval(
        status="pending",
        tool_name="create_ticket",
        tool_args_json=json.dumps(tool_args, ensure_ascii=False),
        requester_id=requester.id,
        execution_result_json="{}",
        idempotency_key=f"approval-{uuid4().hex}",
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)
    return approval


def list_approvals_for_user(db: Session, user: User) -> list[Approval]:
    query = db.query(Approval)
    if user.role in {"admin", "approver"}:
        pass
    else:
        query = query.filter(Approval.requester_id == user.id)
    return query.order_by(Approval.created_at.desc(), Approval.id.desc()).all()


def get_approval_for_user(db: Session, approval_id: int, user: User) -> Approval | None:
    query = db.query(Approval).filter(Approval.id == approval_id)
    if user.role in {"admin", "approver"}:
        return query.first()
    return query.filter(Approval.requester_id == user.id).first()


def _load_tool_args(approval: Approval) -> dict:
    return json.loads(approval.tool_args_json)


def _execute_create_ticket(db: Session, approval: Approval) -> Ticket:
    tool_args = _load_tool_args(approval)
    requester = db.query(User).filter(User.id == tool_args["requester_id"]).one()
    return create_ticket(
        db=db,
        requester=requester,
        title=tool_args["title"],
        description=tool_args["description"],
        category=tool_args["category"],
        priority=tool_args["priority"],
        assignee_id=tool_args.get("assignee_id"),
        source_conversation_id=tool_args.get("source_conversation_id"),
    )


def approve_approval(
    db: Session,
    approval: Approval,
    approver: User,
    decision_comment: str | None = None,
) -> Approval:
    if approval.status == "executed":
        return approval
    if approval.status != "pending":
        raise ValueError("Only pending approvals can be approved")
    if approval.tool_name != "create_ticket":
        raise ValueError("Unsupported approval tool")

    ticket = _execute_create_ticket(db, approval)
    approval.status = "executed"
    approval.approver_id = approver.id
    approval.decision_comment = decision_comment
    approval.execution_result_json = json.dumps(
        {"ticket_id": ticket.id, "ticket_no": ticket.ticket_no},
        ensure_ascii=False,
    )
    approval.decided_at = datetime.now(timezone.utc)
    db.add(approval)
    db.commit()
    db.refresh(approval)
    return approval


def reject_approval(
    db: Session,
    approval: Approval,
    approver: User,
    decision_comment: str | None = None,
) -> Approval:
    if approval.status != "pending":
        raise ValueError("Only pending approvals can be rejected")

    approval.status = "rejected"
    approval.approver_id = approver.id
    approval.decision_comment = decision_comment
    approval.execution_result_json = "{}"
    approval.decided_at = datetime.now(timezone.utc)
    db.add(approval)
    db.commit()
    db.refresh(approval)
    return approval
