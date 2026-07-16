from sqlalchemy import BigInteger, Column, DateTime, Integer, func

from app.db.base import Base


class RAGIndexState(Base):
    __tablename__ = "rag_index_state"

    id = Column(Integer, primary_key=True)
    revision = Column(BigInteger, nullable=False, default=0, server_default="0")
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
