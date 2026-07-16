from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func

from app.db.base import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint(
            "document_version_id",
            "chunk_index",
            name="uq_document_chunks_version_index",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), index=True, nullable=False)
    document_version_id = Column(
        Integer,
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    content_length = Column(Integer, nullable=False)
    page = Column(Integer, nullable=True)
    section = Column(String(255), nullable=True)
    metadata_json = Column(Text, nullable=False)
    embedding_json = Column(Text, nullable=True)
    # Dimensionless storage supports controlled model migrations. Queries cast to
    # the configured model dimension so PostgreSQL can use a matching partial index.
    # SQLite keeps a text variant for lightweight unit tests; production reads/writes
    # this field only on PostgreSQL.
    embedding_vector = Column(Vector().with_variant(Text(), "sqlite"), nullable=True)
    embedding_model = Column(String(120), nullable=True)
    chunk_uid = Column(String(160), unique=True, index=True, nullable=True)
    content_hash = Column(String(64), index=True, nullable=True)
    token_count = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
