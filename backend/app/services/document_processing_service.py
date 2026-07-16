from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.document_version import DocumentVersion
from app.services.embedding_client import EmbeddingClient
from app.services.rag_service import embed_texts_for_model


PARSER_VERSION = "structured-parser-v2"
CHUNKER_VERSION = "boundary-aware-v2"


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


def split_text_on_boundaries(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    normalized = text.strip()
    if not normalized:
        return []
    paragraphs = [part.strip() for part in normalized.split("\n\n") if part.strip()]
    if len(paragraphs) <= 1:
        return split_text_into_chunks(normalized, chunk_size, chunk_overlap)

    chunks: list[str] = []
    current: list[str] = []
    current_length = 0
    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            if current:
                chunks.append("\n\n".join(current))
                current = []
                current_length = 0
            chunks.extend(split_text_into_chunks(paragraph, chunk_size, chunk_overlap))
            continue

        separator_length = 2 if current else 0
        if current and current_length + separator_length + len(paragraph) > chunk_size:
            chunks.append("\n\n".join(current))
            current = [paragraph]
            current_length = len(paragraph)
        else:
            current.append(paragraph)
            current_length += separator_length + len(paragraph)
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _parse_markdown_document(path: Path) -> list[ParsedText]:
    lines = path.read_text(encoding="utf-8").splitlines()
    heading_path: list[str] = []
    current_lines: list[str] = []
    current_section: str | None = None
    sections: list[ParsedText] = []

    def flush() -> None:
        text = "\n".join(current_lines).strip()
        if text:
            sections.append(ParsedText(text=text, page=1, section=current_section))

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            prefix = stripped.split(maxsplit=1)[0]
            if prefix and set(prefix) == {"#"} and len(prefix) <= 6:
                heading = stripped[len(prefix) :].strip()
                if heading:
                    flush()
                    current_lines = [line]
                    level = len(prefix)
                    heading_path = heading_path[: level - 1]
                    heading_path.append(heading)
                    current_section = " > ".join(heading_path)[:255]
                    continue
        current_lines.append(line)
    flush()
    return sections


def _parse_text_document(path: Path, extension: str) -> list[ParsedText]:
    if extension == ".md":
        return _parse_markdown_document(path)
    return [ParsedText(text=path.read_text(encoding="utf-8"), page=1)]


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
    version: DocumentVersion,
    parsed_pages: list[ParsedText],
    chunk_size: int,
    chunk_overlap: int,
    embedding_client: EmbeddingClient | None = None,
    settings: Settings | None = None,
) -> tuple[int, str | None]:
    db.query(DocumentChunk).filter(DocumentChunk.document_version_id == version.id).delete()

    prepared_chunks: list[tuple[str, ParsedText]] = []
    for parsed_page in parsed_pages:
        prepared_chunks.extend(
            (chunk, parsed_page)
            for chunk in split_text_on_boundaries(parsed_page.text, chunk_size, chunk_overlap)
        )

    embeddings = embed_texts_for_model(
        [chunk for chunk, _parsed_page in prepared_chunks],
        embedding_client=embedding_client,
        settings=settings,
    )
    dialect_name = db.get_bind().dialect.name
    for chunk_index, ((chunk, parsed_page), embedding) in enumerate(
        zip(prepared_chunks, embeddings, strict=True)
    ):
        metadata = {
            "document_id": document.id,
            "document_version_id": version.id,
            "version_number": version.version_number,
            "filename": document.original_filename,
            "chunk_index": chunk_index,
            "page": parsed_page.page,
            "section": parsed_page.section,
        }
        chunk_hash = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
        chunk_uid = f"doc-{document.id}-v{version.version_number}-chunk-{chunk_index}-{chunk_hash[:12]}"
        db.add(
            DocumentChunk(
                document_id=document.id,
                document_version_id=version.id,
                chunk_index=chunk_index,
                content=chunk,
                content_length=len(chunk),
                page=parsed_page.page,
                section=parsed_page.section,
                metadata_json=json.dumps(metadata, ensure_ascii=False),
                embedding_json=json.dumps(embedding.vector),
                embedding_vector=embedding.vector if dialect_name == "postgresql" else None,
                embedding_model=embedding.model,
                chunk_uid=chunk_uid,
                content_hash=chunk_hash,
                token_count=max(1, len(chunk) // 2),
            )
        )
    models = sorted({embedding.model for embedding in embeddings})
    embedding_model = models[0] if len(models) == 1 else "mixed" if models else None
    return len(prepared_chunks), embedding_model


def _create_processing_version(db: Session, document: Document) -> DocumentVersion:
    latest_number = (
        db.query(func.max(DocumentVersion.version_number))
        .filter(DocumentVersion.document_id == document.id)
        .scalar()
        or 0
    )
    version = DocumentVersion(
        document_id=document.id,
        version_number=latest_number + 1,
        status="processing",
        content_hash=document.content_hash,
        parser_version=PARSER_VERSION,
        chunker_version=CHUNKER_VERSION,
        chunk_count=0,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def process_document(
    db: Session,
    document: Document,
    storage_dir: str,
    chunk_size: int,
    chunk_overlap: int,
    embedding_client: EmbeddingClient | None = None,
    settings: Settings | None = None,
) -> Document:
    document_id = document.id
    previous_version_id = document.current_version_id
    previous_chunk_count = document.chunk_count
    version = _create_processing_version(db, document)
    if previous_version_id is None:
        document.status = "processing"
    document.error_message = None
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        document_path = Path(storage_dir) / document.storage_path
        parsed_pages = parse_document(document_path, document.file_extension)
        chunk_count, embedding_model = _replace_chunks(
            db,
            document,
            version,
            parsed_pages,
            chunk_size,
            chunk_overlap,
            embedding_client=embedding_client,
            settings=settings,
        )
        if chunk_count == 0:
            raise ValueError("Document did not contain extractable text")

        if previous_version_id is not None:
            previous_version = (
                db.query(DocumentVersion).filter(DocumentVersion.id == previous_version_id).first()
            )
            if previous_version is not None and previous_version.status == "published":
                previous_version.status = "retired"
                db.add(previous_version)

        version.status = "published"
        version.embedding_model = embedding_model
        version.chunk_count = chunk_count
        version.error_message = None
        version.published_at = datetime.now(timezone.utc)
        document.current_version_id = version.id
        document.status = "completed"
        document.chunk_count = chunk_count
        document.error_message = None
        db.add(version)
        db.add(document)
        db.commit()
        db.refresh(document)
        return document
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        failed_version = db.query(DocumentVersion).filter(DocumentVersion.id == version.id).one()
        current_document = db.query(Document).filter(Document.id == document_id).one()
        db.query(DocumentChunk).filter(DocumentChunk.document_version_id == failed_version.id).delete()
        failed_version.status = "failed"
        failed_version.chunk_count = 0
        failed_version.error_message = str(exc)
        if previous_version_id is None:
            current_document.status = "failed"
            current_document.chunk_count = 0
        else:
            current_document.status = "completed"
            current_document.current_version_id = previous_version_id
            current_document.chunk_count = previous_chunk_count
        current_document.error_message = str(exc)
        db.add(failed_version)
        db.add(current_document)
        db.commit()
        db.refresh(current_document)
        return current_document


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
