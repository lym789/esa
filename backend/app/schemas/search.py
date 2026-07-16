from typing import Any, Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    knowledge_base_id: Optional[str] = Field(default=None, min_length=1, max_length=120)


class SearchResultRead(BaseModel):
    chunk_id: int
    document_id: int
    document_name: str
    content: str
    page: Optional[int]
    section: Optional[str]
    similarity: float
    dense_score: float = 0.0
    lexical_score: float = 0.0
    fusion_score: float = 0.0
    rerank_score: float = 0.0
    metadata: dict[str, Any]


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultRead]
    citations: list[str]
    diagnostics: dict[str, Any]
