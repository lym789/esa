from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint

from app.db.base import Base


class DocumentDepartmentACL(Base):
    __tablename__ = "document_department_acls"
    __table_args__ = (
        UniqueConstraint("document_id", "department_id", name="uq_document_department_acl"),
    )

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    department_id = Column(String(120), index=True, nullable=False)
