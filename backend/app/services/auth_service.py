from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User


SEED_USERS = [
    {
        "email": "employee@example.com",
        "name": "Employee User",
        "role": "employee",
        "password": "123456",
    },
    {
        "email": "handler@example.com",
        "name": "Handler User",
        "role": "handler",
        "password": "123456",
    },
    {
        "email": "approver@example.com",
        "name": "Approver User",
        "role": "approver",
        "password": "123456",
    },
    {
        "email": "admin@example.com",
        "name": "Admin User",
        "role": "admin",
        "password": "123456",
    },
]


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email.strip().lower()).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def list_active_handlers(db: Session) -> list[User]:
    return (
        db.query(User)
        .filter(User.role == "handler", User.is_active.is_(True))
        .order_by(User.name.asc(), User.id.asc())
        .all()
    )


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(db, email)
    if user is None or not user.is_active:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


def seed_users(db: Session) -> None:
    for seed_user in SEED_USERS:
        existing_user = get_user_by_email(db, seed_user["email"])
        if existing_user is not None:
            continue

        db.add(
            User(
                email=seed_user["email"],
                name=seed_user["name"],
                role=seed_user["role"],
                hashed_password=hash_password(seed_user["password"]),
                is_active=True,
            )
        )

    db.commit()
