from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


ALLOWED_PRIORITIES = {"low", "medium", "high", "urgent"}
ALLOWED_CATEGORIES = {"IT", "HR", "Finance", "Admin", "Other"}
ALLOWED_STATUSES = {"open", "in_progress", "resolved", "closed"}


class TicketDraftRequest(BaseModel):
    content: str = Field(min_length=1)

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("content cannot be empty")
        return stripped


class TicketDraftRead(BaseModel):
    title: str
    description: str
    category: str
    priority: str
    confidence: float
    reason: str


class TicketCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    category: str = Field(default="Other")
    priority: str = Field(default="medium")
    assignee_id: Optional[int] = None
    source_conversation_id: Optional[int] = None

    @field_validator("title", "description", "category", "priority")
    @classmethod
    def strip_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value cannot be empty")
        return stripped

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        if value not in ALLOWED_CATEGORIES:
            raise ValueError("unsupported category")
        return value

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: str) -> str:
        if value not in ALLOWED_PRIORITIES:
            raise ValueError("unsupported priority")
        return value


class TicketRead(BaseModel):
    id: int
    ticket_no: str
    title: str
    description: str
    category: str
    priority: str
    status: str
    requester_id: int
    assignee_id: Optional[int]
    source_conversation_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TicketStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        stripped = value.strip()
        if stripped not in ALLOWED_STATUSES:
            raise ValueError("Unsupported ticket status")
        return stripped


class TicketAssigneeUpdate(BaseModel):
    assignee_id: Optional[int] = None


class TicketCommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("content cannot be empty")
        return stripped


class TicketCommentRead(BaseModel):
    id: int
    ticket_id: int
    author_id: int
    author_name: str
    author_role: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
