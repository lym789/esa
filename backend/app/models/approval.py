from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.db.base import Base


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String(32), index=True, nullable=False, default="pending")
    tool_name = Column(String(120), index=True, nullable=False)
    tool_args_json = Column(Text, nullable=False)
    requester_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    approver_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    decision_comment = Column(Text, nullable=True)
    execution_result_json = Column(Text, nullable=False, default="{}")
    idempotency_key = Column(String(120), unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    decided_at = Column(DateTime(timezone=True), nullable=True)
