from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.core.config import get_settings
from app.models.user import User
from app.schemas.search import SearchRequest, SearchResponse, SearchResultRead
from app.services.rag_runtime import diagnostics_payload, runtime_metrics
from app.services.rag_service import format_citations, search_with_diagnostics
from app.services.resilience import resilience_registry
from app.services.metrics_exporter import render_prometheus_metrics


router = APIRouter()
settings = get_settings()


@router.get("/metrics")
def get_rag_runtime_metrics(
    _current_user: User = Depends(require_roles(["admin"])),
) -> dict:
    payload = runtime_metrics.snapshot()
    payload["resilience"] = resilience_registry.snapshot()
    return payload


@router.get("/metrics/prometheus")
def get_rag_prometheus_metrics(
    _current_user: User = Depends(require_roles(["admin"])),
) -> Response:
    return Response(
        content=render_prometheus_metrics(),
        media_type="text/plain; version=0.0.4",
    )


@router.post("", response_model=SearchResponse)
def search_chunks(
    payload: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchResponse:
    execution = search_with_diagnostics(
        db=db,
        query=payload.query,
        top_k=payload.top_k,
        similarity_threshold=settings.rag_similarity_threshold,
        user=current_user,
        knowledge_base_id=payload.knowledge_base_id,
    )
    results = execution.results
    return SearchResponse(
        query=payload.query,
        results=[SearchResultRead(**result.__dict__) for result in results],
        citations=format_citations(results),
        diagnostics=diagnostics_payload(execution.diagnostics),
    )
