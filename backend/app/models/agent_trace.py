from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.db.base import Base


class AgentTrace(Base):
    __tablename__ = "agent_traces"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), index=True, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    intent = Column(String(80), index=True, nullable=False)
    user_input = Column(Text, nullable=False)
    intent_json = Column(Text, nullable=False, default="{}")
    retrieved_chunks_json = Column(Text, nullable=False, default="[]")
    llm_input_summary = Column(Text, nullable=True)
    llm_output = Column(Text, nullable=True)
    tool_name = Column(String(120), index=True, nullable=True)
    tool_args_json = Column(Text, nullable=False, default="{}")
    approval_status = Column(String(32), index=True, nullable=False, default="not_required")
    final_result_json = Column(Text, nullable=False, default="{}")
    error_message = Column(Text, nullable=True)
    elapsed_ms = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
