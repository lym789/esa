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


def test_admin_can_queue_async_document_upload(tmp_path, monkeypatch):
    reset_database()
    configure_storage(tmp_path, monkeypatch)
    client = TestClient(app)
    token = login(client, "admin@example.com")

    response = client.post(
        "/api/documents/upload-async",
        headers=auth_header(token),
        files={"file": ("async-policy.md", b"# Policy\nQueued content", "text/markdown")},
    )

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert response.json()["attempt_count"] == 0
    status_response = client.get(
        f"/api/documents/jobs/{response.json()['id']}",
        headers=auth_header(token),
    )
    assert status_response.status_code == 200
    assert status_response.json()["document_id"] == response.json()["document_id"]


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


def test_admin_can_update_document_governance(tmp_path, monkeypatch):
    reset_database()
    configure_storage(tmp_path, monkeypatch)
    client = TestClient(app)
    token = login(client, "admin@example.com")
    document_id = upload_sample_document(client, token).json()["id"]

    response = client.patch(
        f"/api/documents/{document_id}/governance",
        headers=auth_header(token),
        json={
            "publication_status": "published",
            "knowledge_base_id": "finance",
            "visibility": "restricted",
            "classification": "confidential",
            "allowed_roles": ["approver", "admin", "approver"],
            "allowed_departments": ["finance", "finance"],
            "effective_at": None,
            "expires_at": None,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "document_id": document_id,
        "publication_status": "published",
        "knowledge_base_id": "finance",
        "visibility": "restricted",
        "classification": "confidential",
        "allowed_roles": ["admin", "approver"],
        "allowed_departments": ["finance"],
        "effective_at": None,
        "expires_at": None,
    }


def test_admin_can_list_document_versions_after_reindex(tmp_path, monkeypatch):
    reset_database()
    configure_storage(tmp_path, monkeypatch)
    client = TestClient(app)
    token = login(client, "admin@example.com")
    uploaded = upload_sample_document(client, token).json()
    client.post(f"/api/documents/{uploaded['id']}/reindex", headers=auth_header(token))

    response = client.get(
        f"/api/documents/{uploaded['id']}/versions",
        headers=auth_header(token),
    )

    assert response.status_code == 200
    assert [item["version_number"] for item in response.json()] == [2, 1]
    assert [item["status"] for item in response.json()] == ["published", "retired"]


def test_document_governance_requires_admin_and_restricted_roles(tmp_path, monkeypatch):
    reset_database()
    configure_storage(tmp_path, monkeypatch)
    client = TestClient(app)
    admin_token = login(client, "admin@example.com")
    employee_token = login(client, "employee@example.com")
    document_id = upload_sample_document(client, admin_token).json()["id"]
    payload = {
        "publication_status": "published",
        "knowledge_base_id": "default",
        "visibility": "restricted",
        "allowed_roles": [],
        "allowed_departments": [],
    }

    forbidden = client.patch(
        f"/api/documents/{document_id}/governance",
        headers=auth_header(employee_token),
        json={**payload, "allowed_roles": ["employee"]},
    )
    invalid = client.patch(
        f"/api/documents/{document_id}/governance",
        headers=auth_header(admin_token),
        json=payload,
    )

    assert forbidden.status_code == 403
    assert invalid.status_code == 422


def test_confidential_document_requires_restricted_visibility(tmp_path, monkeypatch):
    reset_database()
    configure_storage(tmp_path, monkeypatch)
    client = TestClient(app)
    token = login(client, "admin@example.com")
    document_id = upload_sample_document(client, token).json()["id"]

    response = client.patch(
        f"/api/documents/{document_id}/governance",
        headers=auth_header(token),
        json={
            "publication_status": "published",
            "knowledge_base_id": "default",
            "visibility": "authenticated",
            "classification": "confidential",
            "allowed_roles": [],
            "allowed_departments": [],
        },
    )

    assert response.status_code == 422
