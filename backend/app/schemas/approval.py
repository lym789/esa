from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class ApprovalRead(BaseModel):
    id: int
    status: str
    tool_name: str
    tool_args: dict[str, Any]
    requester_id: int
    approver_id: Optional[int]
    decision_comment: Optional[str]
    execution_result: dict[str, Any]
    idempotency_key: str
    created_at: datetime
    updated_at: datetime
    decided_at: Optional[datetime]


class ApprovalDecisionRequest(BaseModel):
    decision_comment: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("decision_comment")
    @classmethod
    def strip_comment(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None
