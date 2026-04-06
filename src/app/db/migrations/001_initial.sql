CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR(36) PRIMARY KEY,
    file_path TEXT NOT NULL UNIQUE,
    file_name VARCHAR(255) NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    file_type VARCHAR(16) NOT NULL,
    status VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS document_metadata (
    document_id VARCHAR(36) PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
    doc_type VARCHAR(64),
    counterparty_raw VARCHAR(255),
    counterparty_normalized VARCHAR(255),
    document_number VARCHAR(128),
    document_date DATE,
    start_date DATE,
    end_date DATE,
    amount VARCHAR(64),
    currency VARCHAR(32)
);

CREATE TABLE IF NOT EXISTS chunks (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    embedding vector,
    page_from INTEGER,
    page_to INTEGER,
    section_title VARCHAR(255),
    token_count INTEGER NOT NULL,
    CONSTRAINT uq_chunks_document_chunk_index UNIQUE (document_id, chunk_index)
);

CREATE TABLE IF NOT EXISTS users (
    telegram_user_id VARCHAR(64) PRIMARY KEY,
    is_allowed BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS query_logs (
    id VARCHAR(36) PRIMARY KEY,
    telegram_user_id VARCHAR(64) NOT NULL,
    question TEXT NOT NULL,
    normalized_question TEXT NOT NULL,
    answer TEXT NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    latency_ms INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_document_metadata_counterparty
    ON document_metadata (counterparty_normalized);

CREATE INDEX IF NOT EXISTS idx_document_metadata_document_number
    ON document_metadata (document_number);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id
    ON chunks (document_id);

CREATE INDEX IF NOT EXISTS idx_chunks_text_search
    ON chunks
    USING GIN (to_tsvector('russian', text));

CREATE INDEX IF NOT EXISTS idx_query_logs_user_id
    ON query_logs (telegram_user_id);
