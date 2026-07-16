from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.user import User
from app.services.trace_service import create_agent_trace, get_trace, list_traces


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


def test_create_agent_trace_persists_structured_execution_details():
    db = make_session()
    employee = make_user(db, "employee@example.com", "employee")

    trace = create_agent_trace(
        db=db,
        user=employee,
        intent="create_ticket",
        user_input="帮我创建一个 IT 工单",
        tool_name="create_ticket",
        tool_args={"priority": "medium"},
        approval_status="not_required",
        final_result={"ticket_no": "TKT-20260707-0001"},
    )

    assert trace.id is not None
    assert trace.user_id == employee.id
    assert trace.intent == "create_ticket"
    assert trace.tool_name == "create_ticket"
    assert '"priority": "medium"' in trace.tool_args_json
    assert '"ticket_no": "TKT-20260707-0001"' in trace.final_result_json


def test_list_and_get_traces_return_newest_first():
    db = make_session()
    employee = make_user(db, "employee@example.com", "employee")
    first = create_agent_trace(db=db, user=employee, intent="knowledge_qa", user_input="VPN 怎么办")
    second = create_agent_trace(db=db, user=employee, intent="create_ticket", user_input="创建工单")

    traces = list_traces(db)
    found = get_trace(db, first.id)

    assert [trace.id for trace in traces] == [second.id, first.id]
    assert found is not None
    assert found.intent == "knowledge_qa"


def test_create_agent_trace_redacts_pii_and_secrets():
    db = make_session()
    employee = make_user(db, "redaction@example.com", "employee")

    trace = create_agent_trace(
        db=db,
        user=employee,
        intent="knowledge_qa",
        user_input="联系 me@example.com，手机 13812345678，密码=secret123",
        tool_args={"authorization": "opaque", "api_key": "nonstandard-value"},
        llm_output="请联系 me@example.com",
    )

    assert "me@example.com" not in trace.user_input
    assert "13812345678" not in trace.user_input
    assert "secret123" not in trace.user_input
    assert "opaque" not in trace.tool_args_json
    assert "nonstandard-value" not in trace.tool_args_json
    assert "me@example.com" not in trace.llm_output
    assert "REDACTED" in trace.user_input
