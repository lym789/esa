from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.ticket import Ticket
from app.models.user import User
from app.services.approval_service import (
    approve_approval,
    create_ticket_approval,
    reject_approval,
)


def make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
    return testing_session_local()


def make_user(db, email: str, role: str) -> User:
    user = User(email=email, name=email.split("@")[0], role=role, hashed_password="not-used")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_create_ticket_approval_stores_tool_args_without_creating_ticket():
    db = make_session()
    employee = make_user(db, "employee@example.com", "employee")

    approval = create_ticket_approval(
        db=db,
        requester=employee,
        title="邮箱完全无法登录",
        description="公司邮箱完全无法登录",
        category="IT",
        priority="urgent",
    )

    assert approval.status == "pending"
    assert approval.tool_name == "create_ticket"
    assert db.query(Ticket).count() == 0
    assert "邮箱完全无法登录" in approval.tool_args_json


def test_approve_approval_executes_original_ticket_creation_once():
    db = make_session()
    employee = make_user(db, "employee@example.com", "employee")
    approver = make_user(db, "approver@example.com", "approver")
    approval = create_ticket_approval(
        db=db,
        requester=employee,
        title="邮箱完全无法登录",
        description="公司邮箱完全无法登录",
        category="IT",
        priority="urgent",
    )

    executed = approve_approval(db, approval, approver, decision_comment="同意处理")
    executed_again = approve_approval(db, executed, approver, decision_comment="重复通过")

    assert executed.status == "executed"
    assert db.query(Ticket).count() == 1
    assert executed_again.id == executed.id
    assert db.query(Ticket).count() == 1


def test_reject_approval_does_not_create_ticket():
    db = make_session()
    employee = make_user(db, "employee@example.com", "employee")
    approver = make_user(db, "approver@example.com", "approver")
    approval = create_ticket_approval(
        db=db,
        requester=employee,
        title="邮箱完全无法登录",
        description="公司邮箱完全无法登录",
        category="IT",
        priority="urgent",
    )

    rejected = reject_approval(db, approval, approver, decision_comment="信息不足")

    assert rejected.status == "rejected"
    assert rejected.decision_comment == "信息不足"
    assert db.query(Ticket).count() == 0
