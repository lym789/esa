from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.db.base import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_no = Column(String(32), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(64), index=True, nullable=False)
    priority = Column(String(32), index=True, nullable=False)
    status = Column(String(32), index=True, nullable=False, default="open")
    requester_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    assignee_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    source_conversation_id = Column(Integer, ForeignKey("conversations.id"), index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
