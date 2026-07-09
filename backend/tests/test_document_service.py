from io import BytesIO
from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.document import Document
from app.models.user import User
from app.services.document_service import (
    create_document_from_upload,
    delete_document,
    get_document,
    list_documents,
)


def make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
    return testing_session_local()


def make_admin(db):
    user = User(
        email="admin@example.com",
        name="Admin User",
        role="admin",
        hashed_password="not-used",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_upload(filename: str, content: bytes, content_type: str = "text/plain") -> UploadFile:
    return UploadFile(filename=filename, file=BytesIO(content), headers={"content-type": content_type})


def test_create_document_from_upload_saves_file_and_record(tmp_path):
    db = make_session()
    admin = make_admin(db)

    document = create_document_from_upload(
        db=db,
        file=make_upload("IT_VPN_FAQ.md", b"# VPN FAQ\nUse SSO to sign in."),
        uploaded_by=admin,
        storage_dir=str(tmp_path),
    )

    assert document.id is not None
    assert document.original_filename == "IT_VPN_FAQ.md"
    assert document.file_extension == ".md"
    assert document.file_size == 29
    assert document.status == "pending"
    assert document.chunk_count == 0
    assert document.uploaded_by_id == admin.id

    stored_file = tmp_path / document.storage_path
    assert stored_file.exists()
    assert stored_file.read_bytes() == b"# VPN FAQ\nUse SSO to sign in."


def test_create_document_rejects_unsupported_extension(tmp_path):
    db = make_session()
    admin = make_admin(db)

    with pytest.raises(HTTPException) as exc_info:
        create_document_from_upload(
            db=db,
            file=make_upload("installer.exe", b"binary"),
            uploaded_by=admin,
            storage_dir=str(tmp_path),
        )

    assert exc_info.value.status_code == 400
    assert "Unsupported file type" in exc_info.value.detail
    assert db.query(Document).count() == 0


def test_create_document_rejects_empty_file(tmp_path):
    db = make_session()
    admin = make_admin(db)

    with pytest.raises(HTTPException) as exc_info:
        create_document_from_upload(
            db=db,
            file=make_upload("empty.txt", b""),
            uploaded_by=admin,
            storage_dir=str(tmp_path),
        )

    assert exc_info.value.status_code == 400
    assert "empty" in exc_info.value.detail.lower()
    assert db.query(Document).count() == 0


def test_list_and_get_documents_return_created_document(tmp_path):
    db = make_session()
    admin = make_admin(db)
    document = create_document_from_upload(
        db=db,
        file=make_upload("policy.txt", b"Policy text"),
        uploaded_by=admin,
        storage_dir=str(tmp_path),
    )

    documents = list_documents(db)
    found = get_document(db, document.id)

    assert [item.id for item in documents] == [document.id]
    assert found is not None
    assert found.original_filename == "policy.txt"


def test_delete_document_removes_record_and_file(tmp_path):
    db = make_session()
    admin = make_admin(db)
    document = create_document_from_upload(
        db=db,
        file=make_upload("policy.pdf", b"%PDF-1.4 sample", "application/pdf"),
        uploaded_by=admin,
        storage_dir=str(tmp_path),
    )
    stored_file = Path(tmp_path) / document.storage_path
    assert stored_file.exists()

    delete_document(db, document, storage_dir=str(tmp_path))

    assert db.query(Document).count() == 0
    assert not stored_file.exists()
