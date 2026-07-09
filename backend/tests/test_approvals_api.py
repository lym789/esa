from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.models.ticket import Ticket
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


def login(client: TestClient, email: str) -> str:
    response = client.post("/api/auth/login", json={"email": email, "password": "123456"})
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_urgent_ticket_request(client: TestClient, token: str):
    return client.post(
        "/api/tickets",
        headers=auth_header(token),
        json={
            "title": "邮箱完全无法登录",
            "description": "公司邮箱完全无法登录，影响工作",
            "category": "IT",
            "priority": "urgent",
        },
    )


def test_urgent_ticket_creates_pending_approval_instead_of_ticket():
    reset_database()
    client = TestClient(app)
    employee_token = login(client, "employee@example.com")
    approver_token = login(client, "approver@example.com")

    response = create_urgent_ticket_request(client, employee_token)
    ticket_list = client.get("/api/tickets", headers=auth_header(employee_token))
    approval_list = client.get("/api/approvals", headers=auth_header(approver_token))

    assert response.status_code == 202
    assert response.json()["status"] == "pending_approval"
    assert response.json()["approval"]["status"] == "pending"
    assert ticket_list.json() == []
    assert [item["id"] for item in approval_list.json()] == [response.json()["approval"]["id"]]


def test_approver_can_approve_pending_ticket_approval_and_create_ticket():
    reset_database()
    client = TestClient(app)
    employee_token = login(client, "employee@example.com")
    approver_token = login(client, "approver@example.com")
    approval_id = create_urgent_ticket_request(client, employee_token).json()["approval"]["id"]

    approve_response = client.post(
        f"/api/approvals/{approval_id}/approve",
        headers=auth_header(approver_token),
        json={"decision_comment": "同意处理"},
    )
    ticket_list = client.get("/api/tickets", headers=auth_header(employee_token))

    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "executed"
    assert approve_response.json()["execution_result"]["ticket_id"] == ticket_list.json()[0]["id"]
    assert ticket_list.json()[0]["priority"] == "urgent"


def test_approver_can_reject_pending_ticket_approval_without_creating_ticket():
    reset_database()
    client = TestClient(app)
    employee_token = login(client, "employee@example.com")
    approver_token = login(client, "approver@example.com")
    approval_id = create_urgent_ticket_request(client, employee_token).json()["approval"]["id"]

    reject_response = client.post(
        f"/api/approvals/{approval_id}/reject",
        headers=auth_header(approver_token),
        json={"decision_comment": "信息不足"},
    )
    ticket_list = client.get("/api/tickets", headers=auth_header(employee_token))

    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == "rejected"
    assert reject_response.json()["decision_comment"] == "信息不足"
    assert ticket_list.json() == []


def test_employee_cannot_approve_approval():
    reset_database()
    client = TestClient(app)
    employee_token = login(client, "employee@example.com")
    approval_id = create_urgent_ticket_request(client, employee_token).json()["approval"]["id"]

    response = client.post(
        f"/api/approvals/{approval_id}/approve",
        headers=auth_header(employee_token),
        json={"decision_comment": "自己通过"},
    )

    assert response.status_code == 403
    assert TestingSessionLocal().query(Ticket).count() == 0
