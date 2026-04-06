from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class Citation(BaseModel):
    document_id: str
    file_name: str
    page_from: int | None = None
    page_to: int | None = None
    section_title: str | None = None
    snippet: str


class MatchedDocument(BaseModel):
    document_id: str
    file_name: str
    score: float
    matched_chunks: int


class QueryRequest(BaseModel):
    user_id: str
    chat_id: str
    text: str
    trace_id: str = Field(default_factory=lambda: str(uuid4()))

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Текст запроса не может быть пустым.")
        return stripped


class QueryResponse(BaseModel):
    answer: str
    confidence: float
    citations: list[Citation]
    matched_documents: list[MatchedDocument]
    latency_ms: int


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    text: str


class ReindexRequest(BaseModel):
    force: bool = False
    limit: int | None = None


class ReindexResponse(BaseModel):
    started_at: datetime
    finished_at: datetime
    processed_documents: int
    indexed_documents: int
    skipped_documents: int
    ocr_required_documents: int
    failed_documents: int


class HealthResponse(BaseModel):
    status: str
    database_ok: bool
    embedder_ok: bool
    embedding_service_url: str
    openai_configured: bool
    openai_model: str
    documents_dir: str
    documents_dir_exists: bool
    documents_total: int = 0
    indexed_documents: int = 0
    ocr_required_documents: int = 0
    failed_documents: int = 0


class DocumentSummary(BaseModel):
    document_id: str
    file_name: str
    file_type: str
    status: str
    counterparty: str | None = None
    document_number: str | None = None
    updated_at: datetime


class DocumentFragment(BaseModel):
    text: str
    page_from: int | None = None
    page_to: int | None = None
    section_title: str | None = None
    order: int = 0


class ParsedDocument(BaseModel):
    file_path: str
    file_name: str
    file_type: Literal["docx", "pdf"]
    fragments: list[DocumentFragment]

    @property
    def full_text(self) -> str:
        return "\n\n".join(fragment.text for fragment in self.fragments if fragment.text.strip()).strip()


class DocumentMetadataPayload(BaseModel):
    doc_type: str | None = None
    counterparty_raw: str | None = None
    counterparty_normalized: str | None = None
    document_number: str | None = None
    document_date: date | None = None
    start_date: date | None = None
    end_date: date | None = None
    amount: str | None = None
    currency: str | None = None


class ChunkPayload(BaseModel):
    chunk_index: int
    text: str
    page_from: int | None = None
    page_to: int | None = None
    section_title: str | None = None
    token_count: int


class ParsedQuery(BaseModel):
    original_text: str
    normalized_text: str
    question_type: Literal["existence", "end_date", "amount", "generic"] = "generic"
    counterparty: str | None = None
    document_number: str | None = None
    amount_hint: str | None = None
    date_hint: date | None = None


class SearchCandidate(BaseModel):
    candidate_id: str
    document_id: str
    file_name: str
    text: str
    page_from: int | None = None
    page_to: int | None = None
    section_title: str | None = None
    counterparty_normalized: str | None = None
    document_number: str | None = None
    doc_type: str | None = None
    score: float
    source_scores: dict[str, float] = Field(default_factory=dict)


class SearchResult(BaseModel):
    candidates: list[SearchCandidate]
    confidence: float


class GeneratedAnswer(BaseModel):
    text: str
    model: str
