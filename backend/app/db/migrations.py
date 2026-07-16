from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, text


@dataclass(frozen=True)
class Migration:
    version: str
    statements: tuple[str, ...]


MIGRATIONS = (
    Migration(
        version="0001_enterprise_rag_phase1",
        statements=(
            "ALTER TABLE documents ADD COLUMN IF NOT EXISTS publication_status VARCHAR(32) NOT NULL DEFAULT 'published'",
            "ALTER TABLE documents ADD COLUMN IF NOT EXISTS knowledge_base_id VARCHAR(120) NOT NULL DEFAULT 'default'",
            "ALTER TABLE documents ADD COLUMN IF NOT EXISTS visibility VARCHAR(32) NOT NULL DEFAULT 'authenticated'",
            "ALTER TABLE documents ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64)",
            "ALTER TABLE documents ADD COLUMN IF NOT EXISTS effective_at TIMESTAMPTZ",
            "ALTER TABLE documents ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ",
            "ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding_vector vector",
            "ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS chunk_uid VARCHAR(160)",
            "ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64)",
            "ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS token_count INTEGER",
            "CREATE INDEX IF NOT EXISTS ix_documents_publication_status ON documents (publication_status)",
            "CREATE INDEX IF NOT EXISTS ix_documents_knowledge_base_id ON documents (knowledge_base_id)",
            "CREATE INDEX IF NOT EXISTS ix_documents_visibility ON documents (visibility)",
            "CREATE INDEX IF NOT EXISTS ix_documents_content_hash ON documents (content_hash)",
            "CREATE INDEX IF NOT EXISTS ix_documents_effective_at ON documents (effective_at)",
            "CREATE INDEX IF NOT EXISTS ix_documents_expires_at ON documents (expires_at)",
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_document_chunks_chunk_uid ON document_chunks (chunk_uid)",
            "CREATE INDEX IF NOT EXISTS ix_document_chunks_content_hash ON document_chunks (content_hash)",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_document_chunks_document_index ON document_chunks (document_id, chunk_index)",
            "UPDATE document_chunks SET embedding_vector = embedding_json::vector WHERE embedding_vector IS NULL AND embedding_json IS NOT NULL",
            "UPDATE document_chunks SET chunk_uid = 'doc-' || document_id || '-chunk-' || chunk_index WHERE chunk_uid IS NULL",
            "CREATE INDEX IF NOT EXISTS ix_chunks_embedding_local_hnsw ON document_chunks USING hnsw ((embedding_vector::vector(256)) vector_cosine_ops) WHERE embedding_model = 'local-hash-v1' AND embedding_vector IS NOT NULL",
            "CREATE INDEX IF NOT EXISTS ix_chunks_embedding_openai_small_hnsw ON document_chunks USING hnsw ((embedding_vector::vector(1536)) vector_cosine_ops) WHERE embedding_model = 'text-embedding-3-small' AND embedding_vector IS NOT NULL",
        ),
    ),
    Migration(
        version="0002_document_versioning",
        statements=(
            "ALTER TABLE documents ADD COLUMN IF NOT EXISTS current_version_id INTEGER",
            "ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS document_version_id INTEGER",
            "CREATE INDEX IF NOT EXISTS ix_documents_current_version_id ON documents (current_version_id)",
            "CREATE INDEX IF NOT EXISTS ix_document_chunks_document_version_id ON document_chunks (document_version_id)",
            "INSERT INTO document_versions (document_id, version_number, status, content_hash, parser_version, chunker_version, embedding_model, chunk_count, published_at) SELECT d.id, 1, 'published', d.content_hash, 'legacy-v1', 'fixed-char-v1', MIN(dc.embedding_model), d.chunk_count, NOW() FROM documents d JOIN document_chunks dc ON dc.document_id = d.id WHERE d.current_version_id IS NULL GROUP BY d.id ON CONFLICT (document_id, version_number) DO NOTHING",
            "UPDATE documents d SET current_version_id = v.id FROM document_versions v WHERE v.document_id = d.id AND v.version_number = 1 AND d.current_version_id IS NULL",
            "UPDATE document_chunks dc SET document_version_id = d.current_version_id FROM documents d WHERE dc.document_id = d.id AND dc.document_version_id IS NULL AND d.current_version_id IS NOT NULL",
            "ALTER TABLE document_chunks DROP CONSTRAINT IF EXISTS uq_document_chunks_document_index",
            "DROP INDEX IF EXISTS uq_document_chunks_document_index",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_document_chunks_version_index ON document_chunks (document_version_id, chunk_index) WHERE document_version_id IS NOT NULL",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_document_chunks_legacy_index ON document_chunks (document_id, chunk_index) WHERE document_version_id IS NULL",
        ),
    ),
    Migration(
        version="0003_document_processing_jobs",
        statements=(
            "CREATE TABLE IF NOT EXISTS document_processing_jobs (id SERIAL PRIMARY KEY, document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE, requested_by_id INTEGER NOT NULL REFERENCES users(id), status VARCHAR(32) NOT NULL DEFAULT 'queued', attempt_count INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL DEFAULT 3, error_message TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), started_at TIMESTAMPTZ, finished_at TIMESTAMPTZ)",
            "CREATE INDEX IF NOT EXISTS ix_document_processing_jobs_document_id ON document_processing_jobs (document_id)",
            "CREATE INDEX IF NOT EXISTS ix_document_processing_jobs_requested_by_id ON document_processing_jobs (requested_by_id)",
            "CREATE INDEX IF NOT EXISTS ix_document_processing_jobs_status ON document_processing_jobs (status)",
        ),
    ),
    Migration(
        version="0004_hybrid_lexical_retrieval",
        statements=(
            "CREATE EXTENSION IF NOT EXISTS pg_trgm",
            "CREATE INDEX IF NOT EXISTS ix_document_chunks_content_trgm ON document_chunks USING gin (content gin_trgm_ops)",
        ),
    ),
    Migration(
        version="0005_department_acl_and_classification",
        statements=(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS department_id VARCHAR(120)",
            "ALTER TABLE documents ADD COLUMN IF NOT EXISTS classification VARCHAR(32) NOT NULL DEFAULT 'internal'",
            "CREATE INDEX IF NOT EXISTS ix_users_department_id ON users (department_id)",
            "CREATE INDEX IF NOT EXISTS ix_documents_classification ON documents (classification)",
            "CREATE TABLE IF NOT EXISTS document_department_acls (id SERIAL PRIMARY KEY, document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE, department_id VARCHAR(120) NOT NULL, CONSTRAINT uq_document_department_acl UNIQUE (document_id, department_id))",
            "CREATE INDEX IF NOT EXISTS ix_document_department_acls_document_id ON document_department_acls (document_id)",
            "CREATE INDEX IF NOT EXISTS ix_document_department_acls_department_id ON document_department_acls (department_id)",
        ),
    ),
)


def _is_postgresql(engine: Engine) -> bool:
    return engine.dialect.name == "postgresql"


def prepare_postgres_extensions(engine: Engine) -> None:
    if not _is_postgresql(engine):
        return
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


def run_schema_migrations(engine: Engine) -> None:
    if not _is_postgresql(engine):
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(160) PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )

    for migration in MIGRATIONS:
        with engine.begin() as connection:
            already_applied = connection.execute(
                text("SELECT 1 FROM schema_migrations WHERE version = :version"),
                {"version": migration.version},
            ).first()
            if already_applied:
                continue
            for statement in migration.statements:
                connection.execute(text(statement))
            connection.execute(
                text("INSERT INTO schema_migrations (version) VALUES (:version)"),
                {"version": migration.version},
            )
