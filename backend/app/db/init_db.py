from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import (  # noqa: F401
    agent_trace,
    approval,
    conversation,
    document,
    document_chunk,
    document_department_acl,
    document_processing_job,
    document_role_acl,
    document_version,
    message,
    ticket,
    ticket_comment,
    user,
)
from app.db.migrations import prepare_postgres_extensions, run_schema_migrations
from app.services.auth_service import seed_users


def init_db() -> None:
    prepare_postgres_extensions(engine)
    Base.metadata.create_all(bind=engine)
    run_schema_migrations(engine)

    db = SessionLocal()
    try:
        seed_users(db)
    finally:
        db.close()
