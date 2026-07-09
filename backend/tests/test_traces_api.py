import json

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.user import User
from app.services.auth_service import seed_users
from app.services.rag_service import embed_text
from app.services.trace_service import create_agent_trace


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


def login(client: TestClient, email: str) -> str:
    response = client.post("/api/auth/login", json={"email": email, "password": "123456"})
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def add_vpn_chunk():
    db = TestingSessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@example.com").one()
        content = "VPN 登录失败时，请检查统一身份认证和网络连接。"
        document = Document(
            original_filename="IT_VPN_FAQ.md",
            stored_filename="IT_VPN_FAQ.md",
            content_type="text/markdown",
            file_extension=".md",
            file_size=len(content.encode("utf-8")),
            storage_path="documents/IT_VPN_FAQ.md",
            status="completed",
            chunk_count=1,
            uploaded_by_id=admin.id,
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        metadata = {
            "document_id": document.id,
            "filename": document.original_filename,
            "chunk_index": 0,
            "page": 1,
            "section": "VPN 使用说明",
        }
        db.add(
            DocumentChunk(
                document_id=document.id,
                chunk_index=0,
                content=content,
                content_length=len(content),
                page=1,
                section="VPN 使用说明",
                metadata_json=json.dumps(metadata, ensure_ascii=False),
                embedding_json=json.dumps(embed_text(content)),
                embedding_model="local-hash-v1",
            )
        )
        db.commit()
    finally:
        db.close()


def test_admin_can_list_and_get_agent_traces():
    reset_database()
    client = TestClient(app)
    admin_token = login(client, "admin@example.com")
    employee_token = login(client, "employee@example.com")
    db = TestingSessionLocal()
    try:
        employee = db.query(User).filter(User.email == "employee@example.com").one()
        trace = create_agent_trace(
            db=db,
            user=employee,
            intent="create_ticket",
            user_input="帮我创建工单",
            tool_name="create_ticket",
            final_result={"ticket_no": "TKT-20260707-0001"},
        )
        trace_id = trace.id
    finally:
        db.close()

    list_response = client.get("/api/traces", headers=auth_header(admin_token))
    detail_response = client.get(f"/api/traces/{trace_id}", headers=auth_header(admin_token))
    employee_response = client.get("/api/traces", headers=auth_header(employee_token))

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [trace_id]
    assert detail_response.status_code == 200
    assert detail_response.json()["final_result"]["ticket_no"] == "TKT-20260707-0001"
    assert employee_response.status_code == 403


def test_chat_message_writes_conversation_trace(monkeypatch):
    reset_database()
    from app.api import chat as chat_api

    monkeypatch.setattr(chat_api.settings, "rag_similarity_threshold", 0.1)
    add_vpn_chunk()
    client = TestClient(app)
    employee_token = login(client, "employee@example.com")
    admin_token = login(client, "admin@example.com")
    conversation = client.post(
        "/api/chat/conversations",
        headers=auth_header(employee_token),
        json={"title": "VPN 问答"},
    ).json()

    message_response = client.post(
        f"/api/chat/conversations/{conversation['id']}/messages",
        headers=auth_header(employee_token),
        json={"content": "VPN 登录不了怎么办"},
    )
    trace_response = client.get(
        f"/api/chat/conversations/{conversation['id']}/traces",
        headers=auth_header(admin_token),
    )

    assert message_response.status_code == 200
    assert trace_response.status_code == 200
    assert trace_response.json()[0]["intent"] == "knowledge_qa"
    assert trace_response.json()[0]["tool_name"] == "rag_search"
    assert trace_response.json()[0]["approval_status"] == "not_required"


def test_urgent_ticket_and_approval_decision_write_traces():
    reset_database()
    client = TestClient(app)
    employee_token = login(client, "employee@example.com")
    approver_token = login(client, "approver@example.com")
    admin_token = login(client, "admin@example.com")

    approval_response = client.post(
        "/api/tickets",
        headers=auth_header(employee_token),
        json={
            "title": "邮箱完全无法登录",
            "description": "公司邮箱完全无法登录，影响工作",
            "category": "IT",
            "priority": "urgent",
        },
    )
    approval_id = approval_response.json()["approval"]["id"]
    approve_response = client.post(
        f"/api/approvals/{approval_id}/approve",
        headers=auth_header(approver_token),
        json={"decision_comment": "同意处理"},
    )
    trace_response = client.get("/api/traces", headers=auth_header(admin_token))

    assert approval_response.status_code == 202
    assert approve_response.status_code == 200
    traces = trace_response.json()
    assert [trace["approval_status"] for trace in traces] == ["executed", "pending"]
    assert [trace["tool_name"] for trace in traces] == ["approve_approval", "create_approval"]
