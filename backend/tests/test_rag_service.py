import json
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.core.config import Settings
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.user import User
from app.services.embedding_client import FakeEmbeddingClient
from app.services.rag_service import (
    LOCAL_EMBEDDING_DIMENSIONS,
    cosine_similarity,
    embed_text,
    format_citations,
    search,
)


def make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
    return testing_session_local()


def add_document_with_chunk(db, filename: str, content: str, section: Optional[str] = None) -> DocumentChunk:
    user = User(
        email=f"{filename}@example.com",
        name="Test User",
        role="admin",
        hashed_password="not-used",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    document = Document(
        original_filename=filename,
        stored_filename=filename,
        content_type="text/markdown",
        file_extension=".md",
        file_size=len(content.encode("utf-8")),
        storage_path=f"documents/{filename}",
        status="completed",
        chunk_count=1,
        uploaded_by_id=user.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    metadata = {
        "document_id": document.id,
        "filename": filename,
        "chunk_index": 0,
        "page": 1,
        "section": section,
    }
    chunk = DocumentChunk(
        document_id=document.id,
        chunk_index=0,
        content=content,
        content_length=len(content),
        page=1,
        section=section,
        metadata_json=json.dumps(metadata, ensure_ascii=False),
        embedding_json=json.dumps(embed_text(content)),
        embedding_model="local-hash-v1",
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk


def add_document_with_embedding(
    db,
    filename: str,
    content: str,
    embedding: list[float],
    embedding_model: str,
    section: Optional[str] = None,
) -> DocumentChunk:
    chunk = add_document_with_chunk(db, filename, content, section)
    chunk.embedding_json = json.dumps(embedding)
    chunk.embedding_model = embedding_model
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk


def test_embed_text_is_deterministic_and_normalized():
    first = embed_text("VPN 登录 使用统一身份认证")
    second = embed_text("VPN 登录 使用统一身份认证")

    assert first == second
    assert len(first) == LOCAL_EMBEDDING_DIMENSIONS
    assert abs(sum(value * value for value in first) - 1.0) < 0.000001


def test_cosine_similarity_scores_related_text_higher():
    query = embed_text("VPN 登录")
    related = embed_text("VPN 登录需要统一身份认证")
    unrelated = embed_text("食堂报销和差旅流程")

    assert cosine_similarity(query, related) > cosine_similarity(query, unrelated)


def test_search_returns_ranked_chunks_with_metadata():
    db = make_session()
    add_document_with_chunk(db, "IT_VPN_FAQ.md", "VPN 登录失败时，请检查统一身份认证和网络连接。", "VPN 使用说明")
    add_document_with_chunk(db, "HR_POLICY.md", "年假申请需要在系统中提交审批。", "假期制度")

    results = search(db, "VPN 登录不了怎么办", top_k=5, similarity_threshold=0.1)

    assert len(results) == 1
    assert results[0].document_name == "IT_VPN_FAQ.md"
    assert results[0].page == 1
    assert results[0].section == "VPN 使用说明"
    assert results[0].similarity > 0.1
    assert "VPN" in results[0].content
    assert results[0].metadata["filename"] == "IT_VPN_FAQ.md"


def test_search_uses_configured_embedding_client_for_matching_model():
    db = make_session()
    add_document_with_embedding(
        db,
        "IT_VPN_FAQ.md",
        "VPN 登录失败时，请检查统一身份认证。",
        embedding=[1.0, 0.0],
        embedding_model="text-embedding-3-small",
        section="VPN 使用说明",
    )
    embedding_client = FakeEmbeddingClient(vector=[1.0, 0.0], model="text-embedding-3-small")
    settings = Settings(_env_file=None, llm_enabled=True, openai_api_key="sk-test")

    results = search(
        db,
        "VPN 登录不了怎么办",
        top_k=5,
        similarity_threshold=0.9,
        embedding_client=embedding_client,
        settings=settings,
    )

    assert len(results) == 1
    assert results[0].document_name == "IT_VPN_FAQ.md"
    assert embedding_client.calls == ["VPN 登录不了怎么办"]


def test_search_does_not_mix_configured_query_embedding_with_different_chunk_model():
    db = make_session()
    add_document_with_embedding(
        db,
        "LEGACY_REMOTE.md",
        "这是一段旧模型生成的向量内容。",
        embedding=[1.0, 0.0],
        embedding_model="old-embedding-model",
        section="旧模型",
    )
    embedding_client = FakeEmbeddingClient(vector=[1.0, 0.0], model="text-embedding-3-small")
    settings = Settings(_env_file=None, llm_enabled=True, openai_api_key="sk-test")

    results = search(
        db,
        "任何查询",
        top_k=5,
        similarity_threshold=0.1,
        embedding_client=embedding_client,
        settings=settings,
    )

    assert results == []
    assert embedding_client.calls == []


def test_search_filters_results_below_threshold():
    db = make_session()
    add_document_with_chunk(db, "HR_POLICY.md", "年假申请需要在系统中提交审批。", "假期制度")

    results = search(db, "VPN 登录不了怎么办", top_k=5, similarity_threshold=0.95)

    assert results == []


def test_format_citations_uses_document_page_and_section():
    db = make_session()
    add_document_with_chunk(db, "IT_VPN_FAQ.md", "VPN 登录失败时，请检查统一身份认证。", "VPN 使用说明")

    results = search(db, "VPN 登录", top_k=1, similarity_threshold=0.1)
    citations = format_citations(results)

    assert citations == ["[1] IT_VPN_FAQ.md，第 1 页，VPN 使用说明"]
