from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.embedding_client import EmbeddingClient
from app.services.rag_service import embed_text_for_model


@dataclass(frozen=True)
class ParsedText:
    text: str
    page: int
    section: str | None = None


def split_text_into_chunks(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    normalized = text.strip()
    if not normalized:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(normalized):
            break
        start = end - chunk_overlap
    return chunks


def _extract_markdown_section(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            if heading:
                return heading[:255]
    return None


def _parse_text_document(path: Path, extension: str) -> list[ParsedText]:
    text = path.read_text(encoding="utf-8")
    section = _extract_markdown_section(text) if extension == ".md" else None
    return [ParsedText(text=text, page=1, section=section)]


def _parse_pdf_document(path: Path) -> list[ParsedText]:
    reader = PdfReader(str(path))
    pages: list[ParsedText] = []
    for index, page in enumerate(reader.pages, start=1):
        pages.append(ParsedText(text=page.extract_text() or "", page=index))
    return pages


def parse_document(path: Path, extension: str) -> list[ParsedText]:
    if extension in {".md", ".txt"}:
        return _parse_text_document(path, extension)
    if extension == ".pdf":
        return _parse_pdf_document(path)
    raise ValueError(f"Unsupported document extension: {extension}")


def _replace_chunks(
    db: Session,
    document: Document,
    parsed_pages: list[ParsedText],
    chunk_size: int,
    chunk_overlap: int,
    embedding_client: EmbeddingClient | None = None,
    settings: Settings | None = None,
) -> int:
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()

    chunk_index = 0
    for parsed_page in parsed_pages:
        for chunk in split_text_into_chunks(parsed_page.text, chunk_size, chunk_overlap):
            embedding = embed_text_for_model(
                chunk,
                embedding_client=embedding_client,
                settings=settings,
            )
            metadata = {
                "document_id": document.id,
                "filename": document.original_filename,
                "chunk_index": chunk_index,
                "page": parsed_page.page,
                "section": parsed_page.section,
            }
            db.add(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=chunk_index,
                    content=chunk,
                    content_length=len(chunk),
                    page=parsed_page.page,
                    section=parsed_page.section,
                    metadata_json=json.dumps(metadata, ensure_ascii=False),
                    embedding_json=json.dumps(embedding.vector),
                    embedding_model=embedding.model,
                )
            )
            chunk_index += 1
    return chunk_index


def process_document(
    db: Session,
    document: Document,
    storage_dir: str,
    chunk_size: int,
    chunk_overlap: int,
    embedding_client: EmbeddingClient | None = None,
    settings: Settings | None = None,
) -> Document:
    document.status = "processing"
    document.error_message = None
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        document_path = Path(storage_dir) / document.storage_path
        parsed_pages = parse_document(document_path, document.file_extension)
        chunk_count = _replace_chunks(
            db,
            document,
            parsed_pages,
            chunk_size,
            chunk_overlap,
            embedding_client=embedding_client,
            settings=settings,
        )
        if chunk_count == 0:
            raise ValueError("Document did not contain extractable text")

        document.status = "completed"
        document.chunk_count = chunk_count
        document.error_message = None
    except Exception as exc:  # noqa: BLE001
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
        document.status = "failed"
        document.chunk_count = 0
        document.error_message = str(exc)

    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def reindex_completed_documents(
    db: Session,
    storage_dir: str,
    chunk_size: int,
    chunk_overlap: int,
    embedding_client: EmbeddingClient | None = None,
    settings: Settings | None = None,
) -> list[Document]:
    documents = (
        db.query(Document)
        .filter(Document.status == "completed")
        .order_by(Document.id.asc())
        .all()
    )
    return [
        process_document(
            db=db,
            document=document,
            storage_dir=storage_dir,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            embedding_client=embedding_client,
            settings=settings,
        )
        for document in documents
    ]
