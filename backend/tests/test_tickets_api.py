from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.models.ticket import Ticket
from app.models.user import User
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


def test_employee_can_generate_draft_and_create_ticket():
    reset_database()
    client = TestClient(app)
    token = login(client, "employee@example.com")

    draft_response = client.post(
        "/api/tickets/draft",
        headers=auth_header(token),
        json={"content": "帮我创建一个 IT 工单，我的公司邮箱无法登录"},
    )
    create_response = client.post(
        "/api/tickets",
        headers=auth_header(token),
        json={
            "title": draft_response.json()["title"],
            "description": draft_response.json()["description"],
            "category": draft_response.json()["category"],
            "priority": draft_response.json()["priority"],
        },
    )

    assert draft_response.status_code == 200
    assert draft_response.json()["category"] == "IT"
    assert create_response.status_code == 200
    body = create_response.json()
    assert body["ticket_no"].startswith("TKT-")
    assert body["status"] == "open"
    assert body["requester_id"] > 0


def test_ticket_list_and_detail_follow_role_scope():
    reset_database()
    client = TestClient(app)
    employee_token = login(client, "employee@example.com")
    handler_token = login(client, "handler@example.com")
    admin_token = login(client, "admin@example.com")
    own_ticket = client.post(
        "/api/tickets",
        headers=auth_header(employee_token),
        json={
            "title": "邮箱无法登录",
            "description": "邮箱登录失败",
            "category": "IT",
            "priority": "medium",
        },
    ).json()

    db = TestingSessionLocal()
    try:
        handler = db.query(User).filter(User.email == "handler@example.com").one()
        other_employee = User(
            email="other@example.com",
            name="Other Employee",
            role="employee",
            hashed_password="not-used",
        )
        db.add(other_employee)
        db.commit()
        db.refresh(other_employee)
        assigned_ticket = Ticket(
            ticket_no="TKT-20260707-0002",
            title="VPN 无法连接",
            description="VPN 登录失败",
            category="IT",
            priority="high",
            status="open",
            requester_id=other_employee.id,
            assignee_id=handler.id,
        )
        db.add(assigned_ticket)
        db.commit()
        db.refresh(assigned_ticket)
        assigned_ticket_id = assigned_ticket.id
    finally:
        db.close()

    employee_list = client.get("/api/tickets", headers=auth_header(employee_token))
    handler_list = client.get("/api/tickets", headers=auth_header(handler_token))
    admin_list = client.get("/api/tickets", headers=auth_header(admin_token))
    employee_forbidden_detail = client.get(f"/api/tickets/{assigned_ticket_id}", headers=auth_header(employee_token))

    assert [item["id"] for item in employee_list.json()] == [own_ticket["id"]]
    assert [item["id"] for item in handler_list.json()] == [assigned_ticket_id]
    assert {item["id"] for item in admin_list.json()} == {own_ticket["id"], assigned_ticket_id}
    assert employee_forbidden_detail.status_code == 404


def test_tickets_require_authentication():
    reset_database()
    client = TestClient(app)

    response = client.get("/api/tickets")

    assert response.status_code == 401


def test_handler_can_update_assigned_ticket_status():
    reset_database()
    client = TestClient(app)
    employee_token = login(client, "employee@example.com")
    handler_token = login(client, "handler@example.com")

    db = TestingSessionLocal()
    try:
        handler = db.query(User).filter(User.email == "handler@example.com").one()
        handler_id = handler.id
    finally:
        db.close()

    ticket = client.post(
        "/api/tickets",
        headers=auth_header(employee_token),
        json={
            "title": "邮箱无法登录",
            "description": "邮箱登录失败",
            "category": "IT",
            "priority": "medium",
            "assignee_id": handler_id,
        },
    ).json()

    response = client.patch(
        f"/api/tickets/{ticket['id']}/status",
        headers=auth_header(handler_token),
        json={"status": "in_progress"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


def test_employee_cannot_update_ticket_status():
    reset_database()
    client = TestClient(app)
    employee_token = login(client, "employee@example.com")
    ticket = client.post(
        "/api/tickets",
        headers=auth_header(employee_token),
        json={
            "title": "邮箱无法登录",
            "description": "邮箱登录失败",
            "category": "IT",
            "priority": "medium",
        },
    ).json()

    response = client.patch(
        f"/api/tickets/{ticket['id']}/status",
        headers=auth_header(employee_token),
        json={"status": "resolved"},
    )

    assert response.status_code == 403


def test_rejects_invalid_ticket_status_update():
    reset_database()
    client = TestClient(app)
    employee_token = login(client, "employee@example.com")
    admin_token = login(client, "admin@example.com")
    ticket = client.post(
        "/api/tickets",
        headers=auth_header(employee_token),
        json={
            "title": "邮箱无法登录",
            "description": "邮箱登录失败",
            "category": "IT",
            "priority": "medium",
        },
    ).json()

    response = client.patch(
        f"/api/tickets/{ticket['id']}/status",
        headers=auth_header(admin_token),
        json={"status": "waiting"},
    )

    assert response.status_code == 422


def test_employee_and_assigned_handler_can_add_and_list_ticket_comments():
    reset_database()
    client = TestClient(app)
    employee_token = login(client, "employee@example.com")
    handler_token = login(client, "handler@example.com")

    db = TestingSessionLocal()
    try:
        handler = db.query(User).filter(User.email == "handler@example.com").one()
        handler_id = handler.id
    finally:
        db.close()

    ticket = client.post(
        "/api/tickets",
        headers=auth_header(employee_token),
        json={
            "title": "邮箱无法登录",
            "description": "邮箱登录失败",
            "category": "IT",
            "priority": "medium",
            "assignee_id": handler_id,
        },
    ).json()
    first = client.post(
        f"/api/tickets/{ticket['id']}/comments",
        headers=auth_header(employee_token),
        json={"content": "我已经尝试重置密码，仍然失败"},
    )
    second = client.post(
        f"/api/tickets/{ticket['id']}/comments",
        headers=auth_header(handler_token),
        json={"content": "收到，正在检查账号锁定状态"},
    )
    comments = client.get(f"/api/tickets/{ticket['id']}/comments", headers=auth_header(employee_token))

    assert first.status_code == 200
    assert second.status_code == 200
    assert comments.json()[0]["author_name"] == "Employee User"
    assert comments.json()[1]["author_name"] == "Handler User"
    assert [comment["content"] for comment in comments.json()] == [
        "我已经尝试重置密码，仍然失败",
        "收到，正在检查账号锁定状态",
    ]


def test_unrelated_employee_cannot_comment_on_ticket():
    reset_database()
    client = TestClient(app)
    employee_token = login(client, "employee@example.com")

    db = TestingSessionLocal()
    try:
        other_employee = User(
            email="other@example.com",
            name="Other Employee",
            role="employee",
            hashed_password="not-used",
        )
        db.add(other_employee)
        db.commit()
        db.refresh(other_employee)
        ticket = Ticket(
            ticket_no="TKT-20260707-0003",
            title="VPN 无法连接",
            description="VPN 登录失败",
            category="IT",
            priority="high",
            status="open",
            requester_id=other_employee.id,
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        ticket_id = ticket.id
    finally:
        db.close()

    response = client.post(
        f"/api/tickets/{ticket_id}/comments",
        headers=auth_header(employee_token),
        json={"content": "我不应该能评论这张工单"},
    )

    assert response.status_code == 404


def test_admin_can_assign_ticket_to_handler():
    reset_database()
    client = TestClient(app)
    employee_token = login(client, "employee@example.com")
    admin_token = login(client, "admin@example.com")

    db = TestingSessionLocal()
    try:
        handler = db.query(User).filter(User.email == "handler@example.com").one()
        handler_id = handler.id
    finally:
        db.close()

    ticket = client.post(
        "/api/tickets",
        headers=auth_header(employee_token),
        json={
            "title": "邮箱无法登录",
            "description": "邮箱登录失败",
            "category": "IT",
            "priority": "medium",
        },
    ).json()

    response = client.patch(
        f"/api/tickets/{ticket['id']}/assignee",
        headers=auth_header(admin_token),
        json={"assignee_id": handler_id},
    )

    assert response.status_code == 200
    assert response.json()["assignee_id"] == handler_id


def test_employee_cannot_assign_ticket():
    reset_database()
    client = TestClient(app)
    employee_token = login(client, "employee@example.com")

    db = TestingSessionLocal()
    try:
        handler = db.query(User).filter(User.email == "handler@example.com").one()
        handler_id = handler.id
    finally:
        db.close()

    ticket = client.post(
        "/api/tickets",
        headers=auth_header(employee_token),
        json={
            "title": "邮箱无法登录",
            "description": "邮箱登录失败",
            "category": "IT",
            "priority": "medium",
        },
    ).json()

    response = client.patch(
        f"/api/tickets/{ticket['id']}/assignee",
        headers=auth_header(employee_token),
        json={"assignee_id": handler_id},
    )

    assert response.status_code == 403


def test_rejects_assigning_ticket_to_non_handler():
    reset_database()
    client = TestClient(app)
    employee_token = login(client, "employee@example.com")
    admin_token = login(client, "admin@example.com")

    db = TestingSessionLocal()
    try:
        employee = db.query(User).filter(User.email == "employee@example.com").one()
        employee_id = employee.id
    finally:
        db.close()

    ticket = client.post(
        "/api/tickets",
        headers=auth_header(employee_token),
        json={
            "title": "邮箱无法登录",
            "description": "邮箱登录失败",
            "category": "IT",
            "priority": "medium",
        },
    ).json()

    response = client.patch(
        f"/api/tickets/{ticket['id']}/assignee",
        headers=auth_header(admin_token),
        json={"assignee_id": employee_id},
    )

    assert response.status_code == 400
