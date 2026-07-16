import json
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.document_department_acl import DocumentDepartmentACL
from app.models.document_role_acl import DocumentRoleACL
from app.models.user import User
from app.services.rag_service import LOCAL_EMBEDDING_MODEL, embed_text, search


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1",
    reason="set RUN_POSTGRES_TESTS=1 to run PostgreSQL/pgvector integration tests",
)


def test_postgres_vector_search_enforces_acl_inside_database_query():
    database_url = os.environ["DATABASE_URL"]
    engine = create_engine(database_url, future=True)
    connection = engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection)
    unique = uuid4().hex

    try:
        employee = User(
            email=f"rag-employee-{unique}@example.com",
            name="RAG Employee",
            role="employee",
            hashed_password="not-used",
        )
        handler = User(
            email=f"rag-handler-{unique}@example.com",
            name="RAG Handler",
            role="handler",
            hashed_password="not-used",
        )
        finance = User(
            email=f"rag-finance-{unique}@example.com",
            name="RAG Finance",
            role="employee",
            department_id="finance",
            hashed_password="not-used",
        )
        db.add_all([employee, handler, finance])
        db.flush()

        public_document = Document(
            original_filename=f"IT_PUBLIC_{unique}.md",
            stored_filename=f"IT_PUBLIC_{unique}.md",
            content_type="text/markdown",
            file_extension=".md",
            file_size=10,
            storage_path=f"documents/IT_PUBLIC_{unique}.md",
            status="completed",
            publication_status="published",
            knowledge_base_id="default",
            visibility="authenticated",
            chunk_count=1,
            uploaded_by_id=employee.id,
        )
        restricted_document = Document(
            original_filename=f"IT_RESTRICTED_{unique}.md",
            stored_filename=f"IT_RESTRICTED_{unique}.md",
            content_type="text/markdown",
            file_extension=".md",
            file_size=10,
            storage_path=f"documents/IT_RESTRICTED_{unique}.md",
            status="completed",
            publication_status="published",
            knowledge_base_id="default",
            visibility="restricted",
            chunk_count=1,
            uploaded_by_id=employee.id,
        )
        exact_document = Document(
            original_filename=f"ERROR_CODES_{unique}.md",
            stored_filename=f"ERROR_CODES_{unique}.md",
            content_type="text/markdown",
            file_extension=".md",
            file_size=10,
            storage_path=f"documents/ERROR_CODES_{unique}.md",
            status="completed",
            publication_status="published",
            knowledge_base_id="default",
            visibility="authenticated",
            chunk_count=1,
            uploaded_by_id=employee.id,
        )
        db.add_all([public_document, restricted_document, exact_document])
        db.flush()
        db.add(DocumentRoleACL(document_id=restricted_document.id, role="handler"))
        db.add(
            DocumentDepartmentACL(
                document_id=restricted_document.id,
                department_id="finance",
            )
        )

        public_content = "VPN 登录失败时请检查统一身份认证。"
        restricted_content = "VPN 管理员密钥仅限处理人员查看。"
        for index, (document, content) in enumerate(
            [(public_document, public_content), (restricted_document, restricted_content)]
        ):
            vector = embed_text(content)
            db.add(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=0,
                    content=content,
                    content_length=len(content),
                    page=1,
                    section="VPN",
                    metadata_json=json.dumps({"filename": document.original_filename}),
                    embedding_json=json.dumps(vector),
                    embedding_vector=vector,
                    embedding_model=LOCAL_EMBEDDING_MODEL,
                    chunk_uid=f"integration-{unique}-{index}",
                )
            )
        db.flush()

        exact_content = "错误码 ERR-1042 表示统一身份认证令牌过期。"
        exact_vector = embed_text(exact_content)
        db.add(
            DocumentChunk(
                document_id=exact_document.id,
                chunk_index=0,
                content=exact_content,
                content_length=len(exact_content),
                page=1,
                section="错误码",
                metadata_json=json.dumps({"filename": exact_document.original_filename}),
                embedding_json=json.dumps(exact_vector),
                embedding_vector=exact_vector,
                embedding_model="retired-embedding-model",
                chunk_uid=f"integration-{unique}-exact",
            )
        )
        db.flush()

        employee_results = search(db, "VPN 登录", top_k=5, similarity_threshold=0.0, user=employee)
        handler_results = search(db, "VPN 登录", top_k=5, similarity_threshold=0.0, user=handler)
        finance_results = search(db, "VPN 登录", top_k=5, similarity_threshold=0.0, user=finance)

        assert [item.document_name for item in employee_results] == [public_document.original_filename]
        assert {item.document_name for item in handler_results} == {
            public_document.original_filename,
            restricted_document.original_filename,
        }
        assert {item.document_name for item in finance_results} == {
            public_document.original_filename,
            restricted_document.original_filename,
        }
        exact_results = search(db, "ERR-1042", top_k=5, similarity_threshold=0.9, user=employee)
        assert [item.document_name for item in exact_results] == [exact_document.original_filename]
        assert exact_results[0].dense_score == 0.0
        assert exact_results[0].lexical_score > 0.0
    finally:
        db.close()
        transaction.rollback()
        connection.close()
        engine.dispose()
