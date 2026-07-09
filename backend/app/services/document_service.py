from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.user import User


ALLOWED_DOCUMENT_EXTENSIONS = {".md", ".txt", ".pdf"}
DOCUMENT_STORAGE_SUBDIR = "documents"


def _get_extension(filename: str | None) -> str:
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Allowed types: .md, .txt, .pdf",
        )
    return extension


def _read_upload_bytes(file: UploadFile) -> bytes:
    file.file.seek(0)
    content = file.file.read()
    file.file.seek(0)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )
    return content


def create_document_from_upload(
    db: Session,
    file: UploadFile,
    uploaded_by: User,
    storage_dir: str,
) -> Document:
    extension = _get_extension(file.filename)
    content = _read_upload_bytes(file)

    document_dir = Path(storage_dir) / DOCUMENT_STORAGE_SUBDIR
    document_dir.mkdir(parents=True, exist_ok=True)

    stored_filename = f"{uuid4().hex}{extension}"
    relative_storage_path = f"{DOCUMENT_STORAGE_SUBDIR}/{stored_filename}"
    destination = Path(storage_dir) / relative_storage_path
    destination.write_bytes(content)

    document = Document(
        original_filename=file.filename or stored_filename,
        stored_filename=stored_filename,
        content_type=file.content_type or "application/octet-stream",
        file_extension=extension,
        file_size=len(content),
        storage_path=relative_storage_path,
        status="pending",
        chunk_count=0,
        error_message=None,
        uploaded_by_id=uploaded_by.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def list_documents(db: Session) -> list[Document]:
    return db.query(Document).order_by(Document.created_at.desc(), Document.id.desc()).all()


def get_document(db: Session, document_id: int) -> Document | None:
    return db.query(Document).filter(Document.id == document_id).first()


def reset_document_for_reindex(db: Session, document: Document) -> Document:
    document.status = "pending"
    document.chunk_count = 0
    document.error_message = None
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def delete_document(db: Session, document: Document, storage_dir: str) -> None:
    stored_file = Path(storage_dir) / document.storage_path
    stored_file.unlink(missing_ok=True)
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
    db.delete(document)
    db.commit()
