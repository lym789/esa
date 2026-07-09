import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.models.agent_trace import AgentTrace
from app.models.user import User
from app.schemas.trace import TraceRead
from app.services.trace_service import get_trace, list_traces


router = APIRouter()


def trace_to_read(trace: AgentTrace) -> TraceRead:
    return TraceRead(
        id=trace.id,
        conversation_id=trace.conversation_id,
        user_id=trace.user_id,
        intent=trace.intent,
        user_input=trace.user_input,
        intent_data=json.loads(trace.intent_json),
        retrieved_chunks=json.loads(trace.retrieved_chunks_json),
        llm_input_summary=trace.llm_input_summary,
        llm_output=trace.llm_output,
        tool_name=trace.tool_name,
        tool_args=json.loads(trace.tool_args_json),
        approval_status=trace.approval_status,
        final_result=json.loads(trace.final_result_json),
        error_message=trace.error_message,
        elapsed_ms=trace.elapsed_ms,
        created_at=trace.created_at,
    )


@router.get("", response_model=list[TraceRead])
def list_agent_traces(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"])),
) -> list[TraceRead]:
    return [trace_to_read(trace) for trace in list_traces(db)]


@router.get("/{trace_id}", response_model=TraceRead)
def get_agent_trace(
    trace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"])),
) -> TraceRead:
    trace = get_trace(db, trace_id)
    if trace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trace not found",
        )
    return trace_to_read(trace)
