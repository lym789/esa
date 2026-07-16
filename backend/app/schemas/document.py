from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DocumentRead(BaseModel):
    id: int
    original_filename: str
    stored_filename: str
    content_type: str
    file_extension: str
    file_size: int
    storage_path: str
    status: str
    publication_status: str
    knowledge_base_id: str
    visibility: str
    classification: str
    content_hash: Optional[str]
    current_version_id: Optional[int]
    effective_at: Optional[datetime]
    expires_at: Optional[datetime]
    chunk_count: int
    error_message: Optional[str]
    uploaded_by_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentGovernanceUpdate(BaseModel):
    publication_status: Literal["draft", "published", "retired"]
    knowledge_base_id: str = Field(min_length=1, max_length=120)
    visibility: Literal["public", "authenticated", "restricted"]
    classification: Literal["public", "internal", "confidential", "restricted"] = "internal"
    allowed_roles: list[Literal["employee", "handler", "approver", "admin"]] = Field(
        default_factory=list
    )
    allowed_departments: list[str] = Field(default_factory=list, max_length=100)
    effective_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_governance(self):
        normalized_departments = [item.strip() for item in self.allowed_departments if item.strip()]
        if self.visibility == "restricted" and not self.allowed_roles and not normalized_departments:
            raise ValueError("restricted documents require at least one role or department grant")
        if self.classification in {"confidential", "restricted"} and self.visibility != "restricted":
            raise ValueError("confidential and restricted documents must use restricted visibility")
        if any(len(item) > 120 for item in normalized_departments):
            raise ValueError("department identifiers must not exceed 120 characters")
        if self.effective_at and self.expires_at and self.effective_at >= self.expires_at:
            raise ValueError("effective_at must be earlier than expires_at")
        return self


class DocumentGovernanceRead(BaseModel):
    document_id: int
    publication_status: str
    knowledge_base_id: str
    visibility: str
    classification: str
    allowed_roles: list[str]
    allowed_departments: list[str]
    effective_at: Optional[datetime]
    expires_at: Optional[datetime]


class DocumentVersionRead(BaseModel):
    id: int
    document_id: int
    version_number: int
    status: str
    content_hash: Optional[str]
    parser_version: str
    chunker_version: str
    embedding_model: Optional[str]
    chunk_count: int
    error_message: Optional[str]
    created_at: datetime
    published_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class DocumentProcessingJobRead(BaseModel):
    id: int
    document_id: int
    requested_by_id: int
    status: str
    attempt_count: int
    max_attempts: int
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
