import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.models.approval import Approval
from app.models.user import User
from app.schemas.approval import ApprovalDecisionRequest, ApprovalRead
from app.services.approval_service import (
    approve_approval,
    get_approval_for_user,
    list_approvals_for_user,
    reject_approval,
)
from app.services.trace_service import create_agent_trace


router = APIRouter()


def approval_to_read(approval: Approval) -> ApprovalRead:
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


@router.get("", response_model=list[ApprovalRead])
def list_approvals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ApprovalRead]:
    return [approval_to_read(approval) for approval in list_approvals_for_user(db, current_user)]


@router.get("/{approval_id}", response_model=ApprovalRead)
def get_approval(
    approval_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApprovalRead:
    approval = get_approval_for_user(db, approval_id, current_user)
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval not found",
        )
    return approval_to_read(approval)


@router.post("/{approval_id}/approve", response_model=ApprovalRead)
def approve_pending_approval(
    approval_id: int,
    payload: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["approver", "admin"])),
) -> ApprovalRead:
    approval = get_approval_for_user(db, approval_id, current_user)
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval not found",
        )
    try:
        executed = approve_approval(db, approval, current_user, payload.decision_comment)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    tool_args = json.loads(executed.tool_args_json)
    create_agent_trace(
        db=db,
        user=current_user,
        conversation_id=tool_args.get("source_conversation_id"),
        intent="approval_decision",
        user_input=payload.decision_comment or "审批通过",
        intent_data={
            "intent": "approval_decision",
            "approval_id": executed.id,
            "decision": "approve",
        },
        tool_name="approve_approval",
        tool_args={"approval_id": executed.id, "tool_name": executed.tool_name},
        approval_status="executed",
        final_result=json.loads(executed.execution_result_json),
    )
    return approval_to_read(executed)


@router.post("/{approval_id}/reject", response_model=ApprovalRead)
def reject_pending_approval(
    approval_id: int,
    payload: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["approver", "admin"])),
) -> ApprovalRead:
    approval = get_approval_for_user(db, approval_id, current_user)
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval not found",
        )
    try:
        rejected = reject_approval(db, approval, current_user, payload.decision_comment)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    tool_args = json.loads(rejected.tool_args_json)
    create_agent_trace(
        db=db,
        user=current_user,
        conversation_id=tool_args.get("source_conversation_id"),
        intent="approval_decision",
        user_input=payload.decision_comment or "审批拒绝",
        intent_data={
            "intent": "approval_decision",
            "approval_id": rejected.id,
            "decision": "reject",
        },
        tool_name="reject_approval",
        tool_args={"approval_id": rejected.id, "tool_name": rejected.tool_name},
        approval_status="rejected",
        final_result={"approval_id": rejected.id, "status": rejected.status},
    )
    return approval_to_read(rejected)
