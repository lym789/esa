from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import agent_trace, approval, conversation, document, document_chunk, message, ticket, ticket_comment, user  # noqa: F401
from app.services.auth_service import seed_users


def init_db() -> None:
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        seed_users(db)
    finally:
        db.close()
