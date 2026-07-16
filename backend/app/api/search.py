from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import get_settings
from app.models.user import User
from app.schemas.search import SearchRequest, SearchResponse, SearchResultRead
from app.services.rag_service import format_citations, search


router = APIRouter()
settings = get_settings()


@router.post("", response_model=SearchResponse)
def search_chunks(
    payload: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchResponse:
    results = search(
        db=db,
        query=payload.query,
        top_k=payload.top_k,
        similarity_threshold=settings.rag_similarity_threshold,
        user=current_user,
        knowledge_base_id=payload.knowledge_base_id,
    )
    return SearchResponse(
        query=payload.query,
        results=[SearchResultRead(**result.__dict__) for result in results],
        citations=format_citations(results),
    )
