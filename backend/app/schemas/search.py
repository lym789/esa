from typing import Any, Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class SearchResultRead(BaseModel):
    chunk_id: int
    document_id: int
    document_name: str
    content: str
    page: Optional[int]
    section: Optional[str]
    similarity: float
    metadata: dict[str, Any]


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultRead]
    citations: list[str]
