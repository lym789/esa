from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.core.config import get_settings
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentRead
from app.services.document_service import (
    create_document_from_upload,
    delete_document,
    get_document,
    list_documents,
)
from app.services.document_processing_service import process_document


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


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_record(
    document_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(["admin"])),
) -> Response:
    document = _get_existing_document(db, document_id)
    delete_document(db, document, storage_dir=settings.storage_dir)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
