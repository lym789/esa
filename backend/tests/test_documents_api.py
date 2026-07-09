from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.auth_service import seed_users


engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


def reset_database():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        seed_users(db)
    finally:
        db.close()


def configure_storage(tmp_path, monkeypatch):
    from app.api import documents as documents_api

    monkeypatch.setattr(documents_api.settings, "storage_dir", str(tmp_path))


def login(client: TestClient, email: str) -> str:
    response = client.post("/api/auth/login", json={"email": email, "password": "123456"})
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def upload_sample_document(client: TestClient, token: str, filename: str = "IT_VPN_FAQ.md"):
    return client.post(
        "/api/documents/upload",
        headers=auth_header(token),
        files={"file": (filename, b"# VPN FAQ\nUse SSO.", "text/markdown")},
    )


def test_admin_can_upload_document(tmp_path, monkeypatch):
    reset_database()
    configure_storage(tmp_path, monkeypatch)
    client = TestClient(app)
    token = login(client, "admin@example.com")

    response = upload_sample_document(client, token)

    assert response.status_code == 200
    body = response.json()
    assert body["original_filename"] == "IT_VPN_FAQ.md"
    assert body["file_extension"] == ".md"
    assert body["status"] == "completed"
    assert body["chunk_count"] > 0
    assert body["uploaded_by_id"] > 0
    assert (Path(tmp_path) / body["storage_path"]).exists()


def test_employee_cannot_upload_document(tmp_path, monkeypatch):
    reset_database()
    configure_storage(tmp_path, monkeypatch)
    client = TestClient(app)
    token = login(client, "employee@example.com")

    response = upload_sample_document(client, token)

    assert response.status_code == 403


def test_upload_rejects_unsupported_file_type(tmp_path, monkeypatch):
    reset_database()
    configure_storage(tmp_path, monkeypatch)
    client = TestClient(app)
    token = login(client, "admin@example.com")

    response = client.post(
        "/api/documents/upload",
        headers=auth_header(token),
        files={"file": ("installer.exe", b"binary", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_list_and_detail_return_uploaded_document(tmp_path, monkeypatch):
    reset_database()
    configure_storage(tmp_path, monkeypatch)
    client = TestClient(app)
    admin_token = login(client, "admin@example.com")
    employee_token = login(client, "employee@example.com")
    upload_response = upload_sample_document(client, admin_token)
    document_id = upload_response.json()["id"]

    list_response = client.get("/api/documents", headers=auth_header(employee_token))
    detail_response = client.get(f"/api/documents/{document_id}", headers=auth_header(employee_token))

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [document_id]
    assert detail_response.status_code == 200
    assert detail_response.json()["original_filename"] == "IT_VPN_FAQ.md"


def test_reindex_resets_document_status(tmp_path, monkeypatch):
    reset_database()
    configure_storage(tmp_path, monkeypatch)
    client = TestClient(app)
    token = login(client, "admin@example.com")
    document_id = upload_sample_document(client, token).json()["id"]

    db = TestingSessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).one()
        document.status = "failed"
        document.chunk_count = 0
        document.error_message = "parse failed"
        db.commit()
    finally:
        db.close()

    response = client.post(f"/api/documents/{document_id}/reindex", headers=auth_header(token))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["chunk_count"] > 0
    assert body["error_message"] is None


def test_delete_document_removes_document_and_file(tmp_path, monkeypatch):
    reset_database()
    configure_storage(tmp_path, monkeypatch)
    client = TestClient(app)
    token = login(client, "admin@example.com")
    uploaded = upload_sample_document(client, token).json()
    stored_file = Path(tmp_path) / uploaded["storage_path"]
    assert stored_file.exists()

    delete_response = client.delete(f"/api/documents/{uploaded['id']}", headers=auth_header(token))
    list_response = client.get("/api/documents", headers=auth_header(token))

    assert delete_response.status_code == 204
    assert list_response.json() == []
    assert not stored_file.exists()


def test_upload_creates_chunk_records_matching_document_count(tmp_path, monkeypatch):
    reset_database()
    configure_storage(tmp_path, monkeypatch)
    client = TestClient(app)
    token = login(client, "admin@example.com")

    uploaded = upload_sample_document(client, token).json()

    db = TestingSessionLocal()
    try:
        chunk_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == uploaded["id"]).count()
    finally:
        db.close()

    assert uploaded["status"] == "completed"
    assert uploaded["chunk_count"] == chunk_count
    assert chunk_count > 0
