from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.core.config import Settings
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.document_version import DocumentVersion
from app.models.user import User
from app.services.embedding_client import EmbeddingClientError, FakeEmbeddingClient
from app.services.document_processing_service import (
    parse_document,
    process_document,
    reindex_completed_documents,
    split_text_into_chunks,
    split_text_on_boundaries,
)
from app.services.rag_service import LOCAL_EMBEDDING_MODEL


def make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
    return testing_session_local()


def make_document(db, tmp_path: Path, filename: str, content: bytes) -> Document:
    user = User(
        email=f"{filename}@example.com",
        name="Admin User",
        role="admin",
        hashed_password="not-used",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    storage_dir = tmp_path / "storage"
    document_dir = storage_dir / "documents"
    document_dir.mkdir(parents=True, exist_ok=True)
    stored_filename = filename
    storage_path = f"documents/{stored_filename}"
    (storage_dir / storage_path).write_bytes(content)

    document = Document(
        original_filename=filename,
        stored_filename=stored_filename,
        content_type="text/plain",
        file_extension=Path(filename).suffix,
        file_size=len(content),
        storage_path=storage_path,
        status="pending",
        chunk_count=0,
        uploaded_by_id=user.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def test_split_text_into_chunks_uses_overlap():
    text = "abcdefghijklmnopqrstuvwxyz"

    chunks = split_text_into_chunks(text, chunk_size=10, chunk_overlap=3)

    assert chunks == ["abcdefghij", "hijklmnopq", "opqrstuvwx", "vwxyz"]


def test_split_text_on_boundaries_preserves_paragraphs():
    text = "第一段内容。\n\n第二段内容更长。\n\n第三段。"

    chunks = split_text_on_boundaries(text, chunk_size=15, chunk_overlap=3)

    assert chunks == ["第一段内容。", "第二段内容更长。\n\n第三段。"]


def test_parse_markdown_document_preserves_heading_path(tmp_path):
    path = tmp_path / "policy.md"
    path.write_text(
        "# IT 制度\n总则\n\n## VPN\n登录说明\n\n### 故障排查\n检查 SSO。",
        encoding="utf-8",
    )

    parsed = parse_document(path, ".md")

    assert [item.section for item in parsed] == [
        "IT 制度",
        "IT 制度 > VPN",
        "IT 制度 > VPN > 故障排查",
    ]
    assert "检查 SSO" in parsed[-1].text


def test_process_markdown_document_creates_chunks_and_marks_completed(tmp_path):
    db = make_session()
    document = make_document(
        db,
        tmp_path,
        "IT_VPN_FAQ.md",
        "# VPN 使用说明\n\n".encode("utf-8") + ("请使用统一身份认证登录 VPN。\n".encode("utf-8") * 20),
    )

    processed = process_document(
        db=db,
        document=document,
        storage_dir=str(tmp_path / "storage"),
        chunk_size=80,
        chunk_overlap=10,
    )
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).order_by(DocumentChunk.chunk_index).all()

    assert processed.status == "completed"
    assert processed.error_message is None
    assert processed.chunk_count == len(chunks)
    assert processed.chunk_count > 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].page == 1
    assert chunks[0].section == "VPN 使用说明"
    assert "VPN" in chunks[0].content
    assert chunks[0].embedding_json
    assert chunks[0].embedding_model == "local-hash-v1"


def test_process_document_uses_configured_embedding_client(tmp_path):
    db = make_session()
    document = make_document(db, tmp_path, "policy.txt", "VPN 需要统一身份认证登录".encode("utf-8"))
    embedding_client = FakeEmbeddingClient(vector=[0.25, 0.75], model="text-embedding-3-small")
    settings = Settings(_env_file=None, llm_enabled=True, openai_api_key="sk-test")

    processed = process_document(
        db=db,
        document=document,
        storage_dir=str(tmp_path / "storage"),
        chunk_size=80,
        chunk_overlap=10,
        embedding_client=embedding_client,
        settings=settings,
    )
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).all()

    assert processed.status == "completed"
    assert len(chunks) == 1
    assert chunks[0].embedding_json == "[0.25, 0.75]"
    assert chunks[0].embedding_model == "text-embedding-3-small"
    assert embedding_client.calls == ["VPN 需要统一身份认证登录"]


def test_process_document_batches_multiple_embeddings(tmp_path):
    db = make_session()
    document = make_document(
        db,
        tmp_path,
        "policy.md",
        "# 第一节\n第一节内容。\n\n# 第二节\n第二节内容。".encode("utf-8"),
    )

    class BatchOnlyEmbeddingClient:
        def __init__(self):
            self.batches = []

        def embed_texts(self, texts):
            from app.services.embedding_client import EmbeddingResponse

            self.batches.append(list(texts))
            return [
                EmbeddingResponse(vector=[1.0, 0.0], model="text-embedding-3-small")
                for _text in texts
            ]

    client = BatchOnlyEmbeddingClient()
    settings = Settings(_env_file=None, llm_enabled=True, openai_api_key="sk-test")

    processed = process_document(
        db=db,
        document=document,
        storage_dir=str(tmp_path / "storage"),
        chunk_size=80,
        chunk_overlap=10,
        embedding_client=client,
        settings=settings,
    )

    assert processed.chunk_count == 2
    assert len(client.batches) == 1
    assert len(client.batches[0]) == 2


def test_process_document_falls_back_to_local_embedding_when_model_call_fails(tmp_path):
    class FailingEmbeddingClient:
        def embed_text(self, text: str):
            raise EmbeddingClientError("embedding service unavailable")

    db = make_session()
    document = make_document(db, tmp_path, "policy.txt", "邮箱登录失败时请重置密码".encode("utf-8"))
    settings = Settings(_env_file=None, llm_enabled=True, openai_api_key="sk-test")

    processed = process_document(
        db=db,
        document=document,
        storage_dir=str(tmp_path / "storage"),
        chunk_size=80,
        chunk_overlap=10,
        embedding_client=FailingEmbeddingClient(),
        settings=settings,
    )
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).all()

    assert processed.status == "completed"
    assert len(chunks) == 1
    assert chunks[0].embedding_model == LOCAL_EMBEDDING_MODEL
    assert chunks[0].embedding_json


def test_process_document_publishes_new_version_and_keeps_history(tmp_path):
    db = make_session()
    document = make_document(db, tmp_path, "policy.txt", "第一版内容\n第二行".encode("utf-8"))

    first = process_document(db, document, str(tmp_path / "storage"), chunk_size=20, chunk_overlap=5)
    assert first.chunk_count == 1

    stored_file = tmp_path / "storage" / document.storage_path
    stored_file.write_text("新版内容\n" * 12, encoding="utf-8")
    second = process_document(db, document, str(tmp_path / "storage"), chunk_size=25, chunk_overlap=5)
    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_version_id == second.current_version_id)
        .all()
    )
    versions = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.document_id == document.id)
        .order_by(DocumentVersion.version_number)
        .all()
    )

    assert second.status == "completed"
    assert second.chunk_count == len(chunks)
    assert second.chunk_count > 1
    assert [version.status for version in versions] == ["retired", "published"]


def test_reindex_completed_documents_reprocesses_only_completed_documents(tmp_path):
    db = make_session()
    completed = make_document(db, tmp_path, "completed.txt", "第一版内容".encode("utf-8"))
    pending = make_document(db, tmp_path, "pending.txt", "待处理内容".encode("utf-8"))
    process_document(db, completed, str(tmp_path / "storage"), chunk_size=40, chunk_overlap=5)
    embedding_client = FakeEmbeddingClient(vector=[0.5, 0.5], model="text-embedding-3-small")
    settings = Settings(_env_file=None, llm_enabled=True, openai_api_key="sk-test")

    (tmp_path / "storage" / completed.storage_path).write_text("新版 completed 内容", encoding="utf-8")
    reindexed = reindex_completed_documents(
        db=db,
        storage_dir=str(tmp_path / "storage"),
        chunk_size=40,
        chunk_overlap=5,
        embedding_client=embedding_client,
        settings=settings,
    )
    completed_chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_version_id == completed.current_version_id)
        .order_by(DocumentChunk.chunk_index)
        .all()
    )
    pending_chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == pending.id).all()

    assert [document.id for document in reindexed] == [completed.id]
    assert completed_chunks[0].content == "新版 completed 内容"
    assert completed_chunks[0].embedding_model == "text-embedding-3-small"
    assert pending.status == "pending"
    assert pending_chunks == []


def test_failed_reindex_keeps_last_published_version_online(tmp_path):
    db = make_session()
    document = make_document(db, tmp_path, "policy.txt", "稳定版本内容".encode("utf-8"))
    first = process_document(db, document, str(tmp_path / "storage"), chunk_size=40, chunk_overlap=5)
    first_version_id = first.current_version_id
    first_chunk_count = first.chunk_count
    (tmp_path / "storage" / document.storage_path).unlink()

    result = process_document(db, document, str(tmp_path / "storage"), chunk_size=40, chunk_overlap=5)
    versions = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.document_id == document.id)
        .order_by(DocumentVersion.version_number)
        .all()
    )

    assert result.status == "completed"
    assert result.current_version_id == first_version_id
    assert result.chunk_count == first_chunk_count
    assert [version.status for version in versions] == ["published", "failed"]
    assert versions[-1].error_message


def test_process_document_marks_failed_when_file_is_missing(tmp_path):
    db = make_session()
    document = make_document(db, tmp_path, "missing.txt", b"temporary")
    (tmp_path / "storage" / document.storage_path).unlink()

    processed = process_document(
        db=db,
        document=document,
        storage_dir=str(tmp_path / "storage"),
        chunk_size=80,
        chunk_overlap=10,
    )

    assert processed.status == "failed"
    assert processed.chunk_count == 0
    assert processed.error_message
