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


def test_create_list_and_get_conversation():
    reset_database()
    client = TestClient(app)
    token = login(client, "employee@example.com")

    create_response = client.post(
        "/api/chat/conversations",
        headers=auth_header(token),
        json={"title": "VPN 问答"},
    )
    list_response = client.get("/api/chat/conversations", headers=auth_header(token))
    detail_response = client.get(
        f"/api/chat/conversations/{create_response.json()['id']}",
        headers=auth_header(token),
    )

    assert create_response.status_code == 200
    assert create_response.json()["title"] == "VPN 问答"
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [create_response.json()["id"]]
    assert detail_response.status_code == 200
    assert detail_response.json()["messages"] == []


def test_send_message_returns_assistant_answer_with_citations(monkeypatch):
    reset_database()
    from app.api import chat as chat_api

    monkeypatch.setattr(chat_api.settings, "rag_similarity_threshold", 0.1)
    add_vpn_chunk()
    client = TestClient(app)
    token = login(client, "employee@example.com")
    conversation = client.post(
        "/api/chat/conversations",
        headers=auth_header(token),
        json={"title": "VPN 问答"},
    ).json()

    response = client.post(
        f"/api/chat/conversations/{conversation['id']}/messages",
        headers=auth_header(token),
        json={"content": "VPN 登录不了怎么办"},
    )
    detail_response = client.get(f"/api/chat/conversations/{conversation['id']}", headers=auth_header(token))

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "assistant"
    assert "VPN 登录失败" in body["content"]
    assert body["citations"] == ["[1] IT_VPN_FAQ.md，第 1 页，VPN 使用说明"]
    assert [message["role"] for message in detail_response.json()["messages"]] == ["user", "assistant"]


def test_send_message_refuses_without_sources():
    reset_database()
    client = TestClient(app)
    token = login(client, "employee@example.com")
    conversation = client.post(
        "/api/chat/conversations",
        headers=auth_header(token),
        json={"title": "无来源问题"},
    ).json()

    response = client.post(
        f"/api/chat/conversations/{conversation['id']}/messages",
        headers=auth_header(token),
        json={"content": "公司今年年会预算是多少？"},
    )

    assert response.status_code == 200
    assert "没有在当前知识库中找到可靠依据" in response.json()["content"]
    assert response.json()["citations"] == []


def test_user_cannot_access_other_users_conversation():
    reset_database()
    client = TestClient(app)
    employee_token = login(client, "employee@example.com")
    other_token = login(client, "handler@example.com")
    conversation = client.post(
        "/api/chat/conversations",
        headers=auth_header(employee_token),
        json={"title": "私有对话"},
    ).json()

    response = client.get(f"/api/chat/conversations/{conversation['id']}", headers=auth_header(other_token))

    assert response.status_code == 404


def test_chat_requires_authentication():
    reset_database()
    client = TestClient(app)

    response = client.get("/api/chat/conversations")

    assert response.status_code == 401
