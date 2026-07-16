from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.db.base import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), unique=True, nullable=False)
    content_type = Column(String(120), nullable=False)
    file_extension = Column(String(16), index=True, nullable=False)
    file_size = Column(Integer, nullable=False)
    storage_path = Column(String(500), unique=True, nullable=False)
    status = Column(String(32), index=True, nullable=False, default="pending")
    publication_status = Column(
        String(32), index=True, nullable=False, default="published", server_default="published"
    )
    knowledge_base_id = Column(
        String(120), index=True, nullable=False, default="default", server_default="default"
    )
    visibility = Column(
        String(32), index=True, nullable=False, default="authenticated", server_default="authenticated"
    )
    classification = Column(
        String(32), index=True, nullable=False, default="internal", server_default="internal"
    )
    content_hash = Column(String(64), index=True, nullable=True)
    current_version_id = Column(Integer, index=True, nullable=True)
    effective_at = Column(DateTime(timezone=True), index=True, nullable=True)
    expires_at = Column(DateTime(timezone=True), index=True, nullable=True)
    chunk_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
