import json

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.models.approval import Approval
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.user import User
from app.services.auth_service import seed_users
from app.services.ticket_service import create_ticket


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


def reset_database():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        seed_users(db)
    finally:
        db.close()


def login(client: TestClient, email: str) -> str:
    response = client.post("/api/auth/login", json={"email": email, "password": "123456"})
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def seed_dashboard_records() -> tuple[int, int]:
    db = TestingSessionLocal()
    try:
        employee = db.query(User).filter(User.email == "employee@example.com").one()
        document = Document(
            original_filename="VPN 操作手册.md",
            stored_filename="vpn-guide.md",
            content_type="text/markdown",
            file_extension=".md",
            file_size=128,
            storage_path="documents/vpn-guide.md",
            status="completed",
            chunk_count=1,
            uploaded_by_id=employee.id,
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        db.add(
            DocumentChunk(
                document_id=document.id,
                chunk_index=0,
                content="VPN 登录失败时，请检查统一身份认证和网络连接。",
                content_length=25,
                page=1,
                section="登录故障",
                metadata_json="{}",
                embedding_json=None,
            )
        )
        ticket = create_ticket(
            db=db,
            requester=employee,
            title="VPN 无法登录",
            description="连接 VPN 时提示认证失败",
            category="IT",
            priority="medium",
        )
        db.add(
            Approval(
                status="pending",
                tool_name="create_ticket",
                tool_args_json=json.dumps({"title": "申请 VPN 权限"}, ensure_ascii=False),
                requester_id=employee.id,
                execution_result_json="{}",
                idempotency_key="dashboard-test-approval",
            )
        )
        db.commit()
        return document.id, ticket.id
    finally:
        db.close()


def test_dashboard_overview_returns_live_stats_status_notifications_and_integrations():
    reset_database()
    _document_id, ticket_id = seed_dashboard_records()
    client = TestClient(app)
    token = login(client, "employee@example.com")

    response = client.get("/api/dashboard/overview", headers=auth_header(token))

    assert response.status_code == 200
    body = response.json()
    stats = {item["key"]: item for item in body["stats"]}
    assert stats["knowledge_articles"]["value"] == 1
    assert stats["open_tickets"]["value"] == 1
    assert stats["resolved_tickets"]["value"] == 0
    assert body["status"]["backend"] == "online"
    assert body["status"]["database"] == "online"
    assert isinstance(body["status"]["llm_configured"], bool)
    assert body["analytics"]["ticket_status"]["open"] == 1
    assert body["analytics"]["ticket_category"]["IT"] == 1
    assert any(item["href"] == f"/tickets/{ticket_id}" for item in body["notifications"])
    assert {item["key"] for item in body["integrations"]} == {
        "database",
        "llm",
        "embedding",
        "agent_trace",
    }


def test_dashboard_global_search_finds_knowledge_documents_and_visible_tickets():
    reset_database()
    document_id, ticket_id = seed_dashboard_records()
    client = TestClient(app)
    token = login(client, "employee@example.com")

    response = client.get("/api/dashboard/search?q=VPN", headers=auth_header(token))

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "VPN"
    result_pairs = {(item["kind"], item["href"]) for item in body["results"]}
    assert ("knowledge", "/chat") in result_pairs
    assert ("document", f"/admin/documents?document={document_id}") in result_pairs
    assert ("ticket", f"/tickets/{ticket_id}") in result_pairs


def test_dashboard_global_search_hides_other_users_tickets_and_requires_authentication():
    reset_database()
    _document_id, ticket_id = seed_dashboard_records()
    client = TestClient(app)
    handler_token = login(client, "handler@example.com")

    response = client.get("/api/dashboard/search?q=VPN", headers=auth_header(handler_token))
    unauthenticated = client.get("/api/dashboard/search?q=VPN")

    assert response.status_code == 200
    assert f"/tickets/{ticket_id}" not in {item["href"] for item in response.json()["results"]}
    assert unauthenticated.status_code == 401
