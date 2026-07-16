from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.core.config import get_settings
from app.models.document import Document
from app.models.user import User
from app.schemas.document import (
    DocumentGovernanceRead,
    DocumentGovernanceUpdate,
    DocumentProcessingJobRead,
    DocumentRead,
    DocumentVersionRead,
)
from app.services.document_service import (
    create_document_from_upload,
    delete_document,
    get_document,
    list_document_allowed_departments,
    list_document_allowed_roles,
    list_document_versions,
    list_documents,
    update_document_governance,
)
from app.services.document_processing_service import process_document
from app.services.document_job_service import create_processing_job, get_processing_job


router = APIRouter()
settings = get_settings()


def _get_existing_document(db: Session, document_id: int) -> Document:
    document = get_document(db, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return document


@router.post("/upload", response_model=DocumentRead)
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"])),
) -> Document:
    document = create_document_from_upload(
        db=db,
        file=file,
        uploaded_by=current_user,
        storage_dir=settings.storage_dir,
    )
    return process_document(
        db=db,
        document=document,
        storage_dir=settings.storage_dir,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )


@router.post(
    "/upload-async",
    response_model=DocumentProcessingJobRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def upload_document_async(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"])),
):
    document = create_document_from_upload(
        db=db,
        file=file,
        uploaded_by=current_user,
        storage_dir=settings.storage_dir,
    )
    return create_processing_job(db, document, current_user)


@router.get("/jobs/{job_id}", response_model=DocumentProcessingJobRead)
def get_document_processing_job(
    job_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(["admin"])),
):
    job = get_processing_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processing job not found")
    return job


@router.get("", response_model=list[DocumentRead])
def list_document_records(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[Document]:
    return list_documents(db)


@router.get("/{document_id}", response_model=DocumentRead)
def get_document_record(
    document_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> Document:
    return _get_existing_document(db, document_id)


@router.get("/{document_id}/versions", response_model=list[DocumentVersionRead])
def list_document_version_records(
    document_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(["admin"])),
):
    document = _get_existing_document(db, document_id)
    return list_document_versions(db, document)


@router.post("/{document_id}/reindex", response_model=DocumentRead)
def reindex_document(
    document_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(["admin"])),
) -> Document:
    document = _get_existing_document(db, document_id)
    return process_document(
        db=db,
        document=document,
        storage_dir=settings.storage_dir,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )


@router.post(
    "/{document_id}/reindex-async",
    response_model=DocumentProcessingJobRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def reindex_document_async(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"])),
):
    document = _get_existing_document(db, document_id)
    return create_processing_job(db, document, current_user)


@router.patch("/{document_id}/governance", response_model=DocumentGovernanceRead)
def update_document_governance_record(
    document_id: int,
    payload: DocumentGovernanceUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(["admin"])),
) -> DocumentGovernanceRead:
    document = _get_existing_document(db, document_id)
    updated = update_document_governance(
        db,
        document,
        publication_status=payload.publication_status,
        knowledge_base_id=payload.knowledge_base_id,
        visibility=payload.visibility,
        classification=payload.classification,
        allowed_roles=list(payload.allowed_roles),
        allowed_departments=list(payload.allowed_departments),
        effective_at=payload.effective_at,
        expires_at=payload.expires_at,
    )
    return DocumentGovernanceRead(
        document_id=updated.id,
        publication_status=updated.publication_status,
        knowledge_base_id=updated.knowledge_base_id,
        visibility=updated.visibility,
        classification=updated.classification,
        allowed_roles=list_document_allowed_roles(db, updated),
        allowed_departments=list_document_allowed_departments(db, updated),
        effective_at=updated.effective_at,
        expires_at=updated.expires_at,
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_record(
    document_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(["admin"])),
) -> Response:
    document = _get_existing_document(db, document_id)
    delete_document(db, document, storage_dir=settings.storage_dir)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
