from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password, verify_password
from app.db.base import Base
from app.models.user import User
from app.services.auth_service import authenticate_user, seed_users


def make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
    return TestingSessionLocal()


def test_password_hash_verification_round_trip():
    hashed_password = hash_password("123456")

    assert hashed_password != "123456"
    assert verify_password("123456", hashed_password)
    assert not verify_password("wrong-password", hashed_password)


def test_seed_users_creates_four_role_accounts():
    db = make_session()

    seed_users(db)
    seed_users(db)

    users = db.query(User).order_by(User.email).all()
    assert len(users) == 4
    assert {user.email for user in users} == {
        "admin@example.com",
        "approver@example.com",
        "employee@example.com",
        "handler@example.com",
    }
    assert {user.role for user in users} == {"admin", "approver", "employee", "handler"}


def test_authenticate_user_accepts_seed_account_password():
    db = make_session()
    seed_users(db)

    user = authenticate_user(db, "admin@example.com", "123456")

    assert user is not None
    assert user.email == "admin@example.com"
    assert user.role == "admin"


def test_authenticate_user_rejects_bad_credentials():
    db = make_session()
    seed_users(db)

    assert authenticate_user(db, "admin@example.com", "bad-password") is None
    assert authenticate_user(db, "missing@example.com", "123456") is None
