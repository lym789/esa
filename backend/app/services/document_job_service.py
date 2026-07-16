from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.document import Document
from app.models.document_processing_job import DocumentProcessingJob
from app.models.user import User
from app.services.document_processing_service import process_document


def create_processing_job(
    db: Session,
    document: Document,
    requested_by: User,
) -> DocumentProcessingJob:
    existing = (
        db.query(DocumentProcessingJob)
        .filter(
            DocumentProcessingJob.document_id == document.id,
            DocumentProcessingJob.status.in_({"queued", "processing"}),
        )
        .first()
    )
    if existing is not None:
        return existing
    job = DocumentProcessingJob(
        document_id=document.id,
        requested_by_id=requested_by.id,
        status="queued",
        attempt_count=0,
        max_attempts=3,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_processing_job(db: Session, job_id: int) -> DocumentProcessingJob | None:
    return db.query(DocumentProcessingJob).filter(DocumentProcessingJob.id == job_id).first()


def claim_next_processing_job(db: Session) -> DocumentProcessingJob | None:
    query = (
        db.query(DocumentProcessingJob)
        .filter(DocumentProcessingJob.status == "queued")
        .order_by(DocumentProcessingJob.created_at.asc(), DocumentProcessingJob.id.asc())
    )
    if db.get_bind().dialect.name == "postgresql":
        query = query.with_for_update(skip_locked=True)
    job = query.first()
    if job is None:
        return None
    job.status = "processing"
    job.attempt_count += 1
    job.started_at = datetime.now(timezone.utc)
    job.error_message = None
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def execute_processing_job(
    db: Session,
    job: DocumentProcessingJob,
    *,
    settings: Settings | None = None,
) -> DocumentProcessingJob:
    active_settings = settings or get_settings()
    document = db.query(Document).filter(Document.id == job.document_id).first()
    if document is None:
        job.status = "failed"
        job.error_message = "Document not found"
    else:
        processed = process_document(
            db=db,
            document=document,
            storage_dir=active_settings.storage_dir,
            chunk_size=active_settings.chunk_size,
            chunk_overlap=active_settings.chunk_overlap,
            settings=active_settings,
        )
        db.refresh(job)
        if processed.status == "completed" and processed.error_message is None:
            job.status = "completed"
            job.error_message = None
        else:
            job.status = "failed"
            job.error_message = processed.error_message or "Document processing failed"
    job.finished_at = datetime.now(timezone.utc)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def run_next_processing_job(
    db: Session,
    *,
    settings: Settings | None = None,
) -> DocumentProcessingJob | None:
    job = claim_next_processing_job(db)
    if job is None:
        return None
    return execute_processing_job(db, job, settings=settings)

