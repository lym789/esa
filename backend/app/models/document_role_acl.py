from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint

from app.db.base import Base


class DocumentRoleACL(Base):
    __tablename__ = "document_role_acls"
    __table_args__ = (
        UniqueConstraint("document_id", "role", name="uq_document_role_acls_document_role"),
    )

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    role = Column(String(32), index=True, nullable=False)
