from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.core.config import Settings
from app.db.base import Base
from app.main import app
from app.services.auth_service import seed_users
from app.services.rag_runtime import reset_rag_runtime
from app.services.resilience import resilience_registry


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
    reset_rag_runtime()
    db = TestingSessionLocal()
    try:
        seed_users(db)
    finally:
        db.close()


def configure_storage(tmp_path, monkeypatch):
    from app.api import documents as documents_api

    monkeypatch.setattr(documents_api.settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(documents_api.settings, "rag_similarity_threshold", 0.1)


def login(client: TestClient, email: str = "admin@example.com") -> str:
    response = client.post("/api/auth/login", json={"email": email, "password": "123456"})
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def upload_markdown(client: TestClient, token: str, filename: str, content: str):
    return client.post(
        "/api/documents/upload",
        headers=auth_header(token),
        files={"file": (filename, content.encode("utf-8"), "text/markdown")},
    )


def test_authenticated_user_can_search_uploaded_chunks(tmp_path, monkeypatch):
    reset_database()
    configure_storage(tmp_path, monkeypatch)
    client = TestClient(app)
    admin_token = login(client, "admin@example.com")
    employee_token = login(client, "employee@example.com")
    upload = upload_markdown(
        client,
        admin_token,
        "IT_VPN_FAQ.md",
        "# VPN 使用说明\n\nVPN 登录失败时，请检查统一身份认证和网络连接。",
    )
    assert upload.status_code == 200
    assert upload.json()["status"] == "completed"
    assert Path(tmp_path, upload.json()["storage_path"]).exists()

    response = client.post(
        "/api/search",
        headers=auth_header(employee_token),
        json={"query": "VPN 登录不了怎么办", "top_k": 5},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "VPN 登录不了怎么办"
    assert len(body["results"]) == 1
    assert body["results"][0]["document_name"] == "IT_VPN_FAQ.md"
    assert body["results"][0]["similarity"] > 0.1
    assert "VPN" in body["results"][0]["content"]
    assert body["citations"] == ["[1] IT_VPN_FAQ.md，第 1 页，VPN 使用说明"]
    assert body["diagnostics"]["selected_count"] == 1
    assert "total" in body["diagnostics"]["timings_ms"]


def test_rag_runtime_metrics_require_admin_and_report_cache_hits(tmp_path, monkeypatch):
    reset_database()
    configure_storage(tmp_path, monkeypatch)
    client = TestClient(app)
    admin_token = login(client, "admin@example.com")
    employee_token = login(client, "employee@example.com")
    upload_markdown(client, admin_token, "CACHE.md", "# 缓存\nVPN 缓存指标验证。")

    for _ in range(2):
        response = client.post(
            "/api/search",
            headers=auth_header(employee_token),
            json={"query": "VPN 缓存指标", "top_k": 5},
        )
        assert response.status_code == 200
    resilience_registry.execute(
        "reranker:test-provider",
        lambda: "ok",
        settings=Settings(_env_file=None),
        max_concurrency=1,
    )

    forbidden = client.get("/api/search/metrics", headers=auth_header(employee_token))
    metrics = client.get("/api/search/metrics", headers=auth_header(admin_token))

    assert forbidden.status_code == 403
    assert metrics.status_code == 200
    assert metrics.json()["counters"]["searches"] == 2
    assert metrics.json()["counters"]["retrieval_cache_hits"] == 1
    assert metrics.json()["retrieval_cache_hit_rate"] == 0.5
    assert metrics.json()["resilience"]["reranker:test-provider"]["successes"] == 1


def test_search_requires_authentication():
    reset_database()
    client = TestClient(app)

    response = client.post("/api/search", json={"query": "VPN", "top_k": 5})

    assert response.status_code == 401
