from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class TraceRead(BaseModel):
    id: int
    conversation_id: Optional[int]
    user_id: int
    intent: str
    user_input: str
    intent_data: dict[str, Any]
    retrieved_chunks: list[dict[str, Any]]
    llm_input_summary: Optional[str]
    llm_output: Optional[str]
    tool_name: Optional[str]
    tool_args: dict[str, Any]
    approval_status: str
    final_result: dict[str, Any]
    error_message: Optional[str]
    elapsed_ms: int
    created_at: datetime
