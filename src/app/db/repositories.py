from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from sqlalchemy import case, delete, desc, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chunk, Document, DocumentMetadata, DocumentStatus, QueryLog, User
from app.schemas import (
    ChunkPayload,
    ConversationMessage,
    DocumentMetadataPayload,
    DocumentSummary,
    ParsedQuery,
    SearchCandidate,
)


class SearchRepository(Protocol):
    async def search_metadata_candidates(
        self,
        parsed_query: ParsedQuery,
        limit: int,
    ) -> list[SearchCandidate]: ...

    async def search_text_candidates(self, query_text: str, limit: int) -> list[SearchCandidate]: ...

    async def search_vector_candidates(
        self,
        query_vector: list[float],
        limit: int,
    ) -> list[SearchCandidate]: ...


class PostgresRepository(SearchRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_document_by_path(self, file_path: str) -> Document | None:
        result = await self.session.execute(select(Document).where(Document.file_path == file_path))
        return result.scalar_one_or_none()

    async def delete_documents_missing_from_disk(self, existing_paths: set[str]) -> int:
        stmt = select(Document.file_path)
        rows = (await self.session.execute(stmt)).scalars().all()
        missing_paths = [path for path in rows if path not in existing_paths]
        if not missing_paths:
            return 0
        result = await self.session.execute(delete(Document).where(Document.file_path.in_(missing_paths)))
        await self.session.commit()
        return int(result.rowcount or 0)

    async def is_user_allowed(self, telegram_user_id: str) -> bool | None:
        result = await self.session.execute(select(User).where(User.telegram_user_id == telegram_user_id))
        user = result.scalar_one_or_none()
        return None if user is None else user.is_allowed

    async def replace_document_index(
        self,
        *,
        file_path: str,
        file_name: str,
        file_hash: str,
        file_type: str,
        status: str,
        metadata_payload: DocumentMetadataPayload | None,
        chunk_payloads: list[ChunkPayload],
        embeddings: list[list[float]] | None,
    ) -> str:
        document = await self.get_document_by_path(file_path)
        now = datetime.now(timezone.utc)
        if document is None:
            document = Document(
                file_path=file_path,
                file_name=self._trim(file_name, 255) or file_name,
                file_hash=file_hash,
                file_type=self._trim(file_type, 16) or file_type,
                status=self._trim(status, 32) or status,
                created_at=now,
                updated_at=now,
            )
            self.session.add(document)
            await self.session.flush()
        else:
            document.file_name = self._trim(file_name, 255) or file_name
            document.file_hash = file_hash
            document.file_type = self._trim(file_type, 16) or file_type
            document.status = self._trim(status, 32) or status
            document.updated_at = now
            await self.session.execute(delete(Chunk).where(Chunk.document_id == document.id))
            await self.session.execute(
                delete(DocumentMetadata).where(DocumentMetadata.document_id == document.id)
            )

        if metadata_payload is not None:
            self.session.add(
                DocumentMetadata(
                    document_id=document.id,
                    doc_type=self._trim(metadata_payload.doc_type, 64),
                    counterparty_raw=self._trim(metadata_payload.counterparty_raw, 255),
                    counterparty_normalized=self._trim(metadata_payload.counterparty_normalized, 255),
                    document_number=self._trim(metadata_payload.document_number, 128),
                    document_date=metadata_payload.document_date,
                    start_date=metadata_payload.start_date,
                    end_date=metadata_payload.end_date,
                    amount=self._trim(metadata_payload.amount, 64),
                    currency=self._trim(metadata_payload.currency, 32),
                )
            )

        for index, payload in enumerate(chunk_payloads):
            embedding = embeddings[index] if embeddings and index < len(embeddings) else None
            self.session.add(
                Chunk(
                    document_id=document.id,
                    chunk_index=payload.chunk_index,
                    text=payload.text,
                    embedding=embedding,
                    page_from=payload.page_from,
                    page_to=payload.page_to,
                    section_title=self._trim(payload.section_title, 255),
                    token_count=payload.token_count,
                )
            )

        await self.session.commit()
        return document.id

    async def list_documents(self, limit: int = 100) -> list[DocumentSummary]:
        stmt = (
            select(Document, DocumentMetadata)
            .outerjoin(DocumentMetadata, DocumentMetadata.document_id == Document.id)
            .order_by(desc(Document.updated_at))
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            DocumentSummary(
                document_id=document.id,
                file_name=document.file_name,
                file_type=document.file_type,
                status=document.status,
                counterparty=metadata.counterparty_normalized if metadata else None,
                document_number=metadata.document_number if metadata else None,
                updated_at=document.updated_at,
            )
            for document, metadata in rows
        ]

    async def healthcheck(self) -> bool:
        try:
            await self.session.execute(select(literal(1)))
            return True
        except Exception:
            return False

    async def get_document_status_counts(self) -> dict[str, int]:
        stmt = select(Document.status, func.count(Document.id)).group_by(Document.status)
        rows = (await self.session.execute(stmt)).all()
        counts = {status: int(count) for status, count in rows}
        return {
            "total": sum(counts.values()),
            "indexed": counts.get(DocumentStatus.INDEXED.value, 0),
            "ocr_required": counts.get(DocumentStatus.OCR_REQUIRED.value, 0),
            "failed": counts.get(DocumentStatus.FAILED.value, 0),
        }

    async def log_query(
        self,
        *,
        telegram_user_id: str,
        question: str,
        normalized_question: str,
        answer: str,
        confidence: float,
        latency_ms: int,
    ) -> None:
        self.session.add(
            QueryLog(
                telegram_user_id=telegram_user_id,
                question=question,
                normalized_question=normalized_question,
                answer=answer,
                confidence=confidence,
                latency_ms=latency_ms,
            )
        )
        await self.session.commit()

    async def get_recent_conversation_messages(
        self,
        telegram_user_id: str,
        limit_messages: int,
    ) -> list[ConversationMessage]:
        normalized_limit = max(0, limit_messages)
        if normalized_limit == 0:
            return []

        turns_limit = max(1, (normalized_limit + 1) // 2)
        stmt = (
            select(QueryLog)
            .where(QueryLog.telegram_user_id == telegram_user_id)
            .order_by(desc(QueryLog.created_at), desc(QueryLog.id))
            .limit(turns_limit)
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        rows.reverse()

        messages: list[ConversationMessage] = []
        for row in rows:
            question = " ".join(row.question.split()).strip()
            if question:
                messages.append(ConversationMessage(role="user", text=question))

            answer = " ".join(row.answer.split()).strip()
            if answer:
                messages.append(ConversationMessage(role="assistant", text=answer))

        return messages[-normalized_limit:]

    async def search_metadata_candidates(
        self,
        parsed_query: ParsedQuery,
        limit: int,
    ) -> list[SearchCandidate]:
        score_expr = literal(0.0)
        has_filter = False
        conditions = [Document.status == DocumentStatus.INDEXED.value]

        if parsed_query.counterparty:
            has_filter = True
            normalized = parsed_query.counterparty
            score_expr = score_expr + case(
                (DocumentMetadata.counterparty_normalized == normalized, 3.5),
                (DocumentMetadata.counterparty_normalized.ilike(f"%{normalized}%"), 2.0),
                else_=0.0,
            )
            conditions.append(DocumentMetadata.counterparty_normalized.ilike(f"%{normalized}%"))

        if parsed_query.document_number:
            has_filter = True
            score_expr = score_expr + case(
                (DocumentMetadata.document_number == parsed_query.document_number, 3.0),
                (DocumentMetadata.document_number.ilike(f"%{parsed_query.document_number}%"), 1.5),
                else_=0.0,
            )
            conditions.append(DocumentMetadata.document_number.ilike(f"%{parsed_query.document_number}%"))

        if not has_filter:
            return []

        stmt = (
            select(Chunk, Document, DocumentMetadata, score_expr.label("score"))
            .join(Document, Chunk.document_id == Document.id)
            .join(DocumentMetadata, DocumentMetadata.document_id == Document.id)
            .where(*conditions)
            .order_by(desc("score"), Chunk.chunk_index)
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        return [self._candidate_from_row(row, "metadata") for row in rows]

    async def search_text_candidates(self, query_text: str, limit: int) -> list[SearchCandidate]:
        ts_query = func.websearch_to_tsquery("russian", query_text)
        ts_vector = func.to_tsvector("russian", Chunk.text)
        rank = func.ts_rank_cd(ts_vector, ts_query)
        stmt = (
            select(Chunk, Document, DocumentMetadata, rank.label("score"))
            .join(Document, Chunk.document_id == Document.id)
            .outerjoin(DocumentMetadata, DocumentMetadata.document_id == Document.id)
            .where(Document.status == DocumentStatus.INDEXED.value)
            .where(ts_vector.op("@@")(ts_query))
            .order_by(desc("score"))
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        return [self._candidate_from_row(row, "text") for row in rows]

    async def search_vector_candidates(
        self,
        query_vector: list[float],
        limit: int,
    ) -> list[SearchCandidate]:
        distance = Chunk.embedding.cosine_distance(query_vector)
        score = (1 - distance).label("score")
        stmt = (
            select(Chunk, Document, DocumentMetadata, score)
            .join(Document, Chunk.document_id == Document.id)
            .outerjoin(DocumentMetadata, DocumentMetadata.document_id == Document.id)
            .where(Document.status == DocumentStatus.INDEXED.value)
            .where(Chunk.embedding.is_not(None))
            .order_by(distance)
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        return [self._candidate_from_row(row, "vector") for row in rows]

    def _candidate_from_row(
        self,
        row: tuple[Chunk, Document, DocumentMetadata | None, float],
        source: str,
    ) -> SearchCandidate:
        chunk, document, metadata, score = row
        return SearchCandidate(
            candidate_id=chunk.id,
            document_id=document.id,
            file_name=document.file_name,
            text=chunk.text,
            page_from=chunk.page_from,
            page_to=chunk.page_to,
            section_title=chunk.section_title,
            counterparty_normalized=metadata.counterparty_normalized if metadata else None,
            document_number=metadata.document_number if metadata else None,
            doc_type=metadata.doc_type if metadata else None,
            score=float(score or 0.0),
            source_scores={source: float(score or 0.0)},
        )

    @staticmethod
    def _trim(value: str | None, limit: int) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        return normalized[:limit]
