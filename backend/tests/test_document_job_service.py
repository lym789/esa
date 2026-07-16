from io import BytesIO

from fastapi import UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.base import Base
from app.models.document import Document
from app.models.user import User
from app.services.document_job_service import create_processing_job, run_next_processing_job
from app.services.document_service import create_document_from_upload


def make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
    return testing_session_local()


def make_admin(db):
    user = User(
        email="job-admin@example.com",
        name="Job Admin",
        role="admin",
        hashed_password="not-used",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def upload(db, admin, tmp_path):
    return create_document_from_upload(
        db=db,
        file=UploadFile(
            filename="policy.md",
            file=BytesIO(b"# VPN\nUse SSO to sign in."),
            headers={"content-type": "text/markdown"},
        ),
        uploaded_by=admin,
        storage_dir=str(tmp_path),
    )


def test_processing_job_is_durable_idempotent_and_completes(tmp_path):
    db = make_session()
    admin = make_admin(db)
    document = upload(db, admin, tmp_path)

    first = create_processing_job(db, document, admin)
    duplicate = create_processing_job(db, document, admin)
    completed = run_next_processing_job(
        db,
        settings=Settings(
            _env_file=None,
            storage_dir=str(tmp_path),
            chunk_size=80,
            chunk_overlap=10,
        ),
    )
    db.refresh(document)

    assert duplicate.id == first.id
    assert completed is not None
    assert completed.status == "completed"
    assert completed.attempt_count == 1
    assert completed.started_at is not None
    assert completed.finished_at is not None
    assert document.status == "completed"
    assert document.current_version_id is not None


def test_processing_job_records_failure(tmp_path):
    db = make_session()
    admin = make_admin(db)
    document = upload(db, admin, tmp_path)
    create_processing_job(db, document, admin)
    (tmp_path / document.storage_path).unlink()

    failed = run_next_processing_job(
        db,
        settings=Settings(
            _env_file=None,
            storage_dir=str(tmp_path),
            chunk_size=80,
            chunk_overlap=10,
        ),
    )
    db.refresh(document)

    assert failed is not None
    assert failed.status == "failed"
    assert failed.error_message
    assert document.status == "failed"

