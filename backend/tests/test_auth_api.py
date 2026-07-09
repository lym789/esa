from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db, require_roles
from app.db.base import Base
from app.main import app
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


@app.get("/_test/admin-only")
def admin_only(_user=Depends(require_roles(["admin"]))):
    return {"status": "allowed"}


def reset_database():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        seed_users(db)
    finally:
        db.close()


def test_login_returns_token_and_user_profile():
    reset_database()
    client = TestClient(app)

    response = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "123456"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "admin@example.com"
    assert body["user"]["role"] == "admin"


def test_login_rejects_invalid_credentials():
    reset_database()
    client = TestClient(app)

    response = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "wrong"},
    )

    assert response.status_code == 401


def test_me_returns_current_user_for_valid_token():
    reset_database()
    client = TestClient(app)
    login = client.post(
        "/api/auth/login",
        json={"email": "employee@example.com", "password": "123456"},
    )
    token = login.json()["access_token"]

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "employee@example.com"
    assert body["role"] == "employee"


def test_me_rejects_missing_token():
    reset_database()
    client = TestClient(app)

    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_require_roles_allows_admin_and_denies_employee():
    reset_database()
    client = TestClient(app)
    admin_login = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "123456"},
    )
    employee_login = client.post(
        "/api/auth/login",
        json={"email": "employee@example.com", "password": "123456"},
    )

    admin_response = client.get(
        "/_test/admin-only",
        headers={"Authorization": f"Bearer {admin_login.json()['access_token']}"},
    )
    employee_response = client.get(
        "/_test/admin-only",
        headers={"Authorization": f"Bearer {employee_login.json()['access_token']}"},
    )

    assert admin_response.status_code == 200
    assert employee_response.status_code == 403


def test_admin_can_list_active_handlers():
    reset_database()
    client = TestClient(app)
    admin_login = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "123456"},
    )

    response = client.get(
        "/api/auth/handlers",
        headers={"Authorization": f"Bearer {admin_login.json()['access_token']}"},
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": response.json()[0]["id"],
            "email": "handler@example.com",
            "name": "Handler User",
            "role": "handler",
        }
    ]


def test_employee_cannot_list_handlers():
    reset_database()
    client = TestClient(app)
    employee_login = client.post(
        "/api/auth/login",
        json={"email": "employee@example.com", "password": "123456"},
    )

    response = client.get(
        "/api/auth/handlers",
        headers={"Authorization": f"Bearer {employee_login.json()['access_token']}"},
    )

    assert response.status_code == 403
