from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.base import Base
from app.models.ticket import Ticket
from app.models.user import User
from app.services.llm_client import FakeLLMClient, LLMClientError
from app.services.ticket_service import (
    create_ticket_comment,
    create_ticket,
    generate_ticket_draft,
    get_ticket_for_user,
    list_ticket_comments,
    list_tickets_for_user,
    update_ticket_status,
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


def test_generate_ticket_draft_extracts_category_priority_and_title():
    draft = generate_ticket_draft("帮我创建一个紧急 IT 工单，我的公司邮箱完全无法登录")

    assert draft.category == "IT"
    assert draft.priority == "urgent"
    assert "邮箱" in draft.title
    assert "公司邮箱完全无法登录" in draft.description


def test_generate_ticket_draft_uses_llm_when_configured():
    llm_client = FakeLLMClient(
        json_response={
            "title": "公司邮箱无法登录",
            "description": "用户反馈公司邮箱无法登录，影响正常办公。",
            "category": "IT",
            "priority": "medium",
            "confidence": 0.88,
            "reason": "描述中出现邮箱、登录等 IT 支持关键词。",
        },
        model="fake-llm-v1",
    )
    settings = Settings(_env_file=None, llm_enabled=True, openai_api_key="sk-test")

    draft = generate_ticket_draft(
        "帮我创建一个工单，我的公司邮箱无法登录",
        llm_client=llm_client,
        settings=settings,
    )

    assert draft.title == "公司邮箱无法登录"
    assert draft.description == "用户反馈公司邮箱无法登录，影响正常办公。"
    assert draft.category == "IT"
    assert draft.priority == "medium"
    assert draft.confidence == 0.88
    assert "邮箱" in draft.reason
    assert llm_client.calls[0]["mode"] == "json"
    assert "工单草稿" in llm_client.calls[0]["messages"][0]["content"]


def test_generate_ticket_draft_falls_back_when_llm_output_is_invalid():
    llm_client = FakeLLMClient(
        json_response={
            "title": "无效输出",
            "description": "无效输出",
            "category": "Legal",
            "priority": "critical",
            "confidence": 0.9,
            "reason": "模型输出了不允许的枚举值。",
        }
    )
    settings = Settings(_env_file=None, llm_enabled=True, openai_api_key="sk-test")

    draft = generate_ticket_draft(
        "帮我创建一个紧急 IT 工单，我的公司邮箱完全无法登录",
        llm_client=llm_client,
        settings=settings,
    )

    assert draft.category == "IT"
    assert draft.priority == "urgent"
    assert "邮箱" in draft.title
    assert "关键词" in draft.reason


def test_generate_ticket_draft_falls_back_when_llm_fails():
    llm_client = FakeLLMClient(error=LLMClientError("model unavailable"))
    settings = Settings(_env_file=None, llm_enabled=True, openai_api_key="sk-test")

    draft = generate_ticket_draft(
        "帮我创建一个紧急 IT 工单，我的公司邮箱完全无法登录",
        llm_client=llm_client,
        settings=settings,
    )

    assert draft.category == "IT"
    assert draft.priority == "urgent"
    assert "邮箱" in draft.title


def test_create_ticket_assigns_daily_ticket_number():
    db = make_session()
    employee = make_user(db, "employee@example.com", "employee")

    first = create_ticket(
        db,
        requester=employee,
        title="邮箱无法登录",
        description="邮箱登录失败",
        category="IT",
        priority="medium",
    )
    second = create_ticket(
        db,
        requester=employee,
        title="VPN 无法连接",
        description="VPN 登录失败",
        category="IT",
        priority="high",
    )

    assert first.ticket_no.startswith("TKT-")
    assert first.ticket_no.endswith("-0001")
    assert second.ticket_no.endswith("-0002")
    assert first.status == "open"
    assert first.requester_id == employee.id


def test_list_tickets_is_scoped_by_role():
    db = make_session()
    employee = make_user(db, "employee@example.com", "employee")
    other_employee = make_user(db, "other@example.com", "employee")
    handler = make_user(db, "handler@example.com", "handler")
    admin = make_user(db, "admin@example.com", "admin")
    own_ticket = create_ticket(db, employee, "邮箱无法登录", "邮箱登录失败", "IT", "medium")
    assigned_ticket = create_ticket(db, other_employee, "VPN 无法连接", "VPN 登录失败", "IT", "high")
    assigned_ticket.assignee_id = handler.id
    db.commit()

    assert [ticket.id for ticket in list_tickets_for_user(db, employee)] == [own_ticket.id]
    assert [ticket.id for ticket in list_tickets_for_user(db, handler)] == [assigned_ticket.id]
    assert {ticket.id for ticket in list_tickets_for_user(db, admin)} == {own_ticket.id, assigned_ticket.id}


def test_get_ticket_for_user_rejects_unrelated_employee():
    db = make_session()
    employee = make_user(db, "employee@example.com", "employee")
    other_employee = make_user(db, "other@example.com", "employee")
    ticket = create_ticket(db, other_employee, "VPN 无法连接", "VPN 登录失败", "IT", "high")

    assert get_ticket_for_user(db, ticket.id, employee) is None
    assert isinstance(get_ticket_for_user(db, ticket.id, other_employee), Ticket)


def test_handler_can_update_assigned_ticket_status():
    db = make_session()
    employee = make_user(db, "employee@example.com", "employee")
    handler = make_user(db, "handler@example.com", "handler")
    ticket = create_ticket(db, employee, "邮箱无法登录", "邮箱登录失败", "IT", "medium")
    ticket.assignee_id = handler.id
    db.commit()

    updated = update_ticket_status(db, ticket, handler, "in_progress")

    assert updated.status == "in_progress"


def test_employee_cannot_update_ticket_status():
    db = make_session()
    employee = make_user(db, "employee@example.com", "employee")
    ticket = create_ticket(db, employee, "邮箱无法登录", "邮箱登录失败", "IT", "medium")

    try:
        update_ticket_status(db, ticket, employee, "resolved")
    except ValueError as exc:
        assert "Only handlers or admins" in str(exc)
    else:
        raise AssertionError("employee status update should fail")

    assert ticket.status == "open"


def test_rejects_unsupported_ticket_status():
    db = make_session()
    employee = make_user(db, "employee@example.com", "employee")
    admin = make_user(db, "admin@example.com", "admin")
    ticket = create_ticket(db, employee, "邮箱无法登录", "邮箱登录失败", "IT", "medium")

    try:
        update_ticket_status(db, ticket, admin, "waiting")
    except ValueError as exc:
        assert "Unsupported ticket status" in str(exc)
    else:
        raise AssertionError("unsupported status update should fail")


def test_create_and_list_ticket_comments_in_created_order():
    db = make_session()
    employee = make_user(db, "employee@example.com", "employee")
    handler = make_user(db, "handler@example.com", "handler")
    ticket = create_ticket(db, employee, "邮箱无法登录", "邮箱登录失败", "IT", "medium")
    ticket.assignee_id = handler.id
    db.commit()

    first = create_ticket_comment(db, ticket, employee, "我已经尝试重置密码，仍然失败")
    second = create_ticket_comment(db, ticket, handler, "收到，正在检查账号锁定状态")
    comments = list_ticket_comments(db, ticket)

    assert [comment.id for comment in comments] == [first.id, second.id]
    assert comments[0].author_id == employee.id
    assert comments[1].content == "收到，正在检查账号锁定状态"
