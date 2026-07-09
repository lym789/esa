from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    id: int
    original_filename: str
    stored_filename: str
    content_type: str
    file_extension: str
    file_size: int
    storage_path: str
    status: str
    chunk_count: int
    error_message: Optional[str]
    uploaded_by_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
