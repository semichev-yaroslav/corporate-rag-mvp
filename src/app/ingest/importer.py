from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

from app.db.models import DocumentStatus
from app.providers.embedding_client import EmbeddingHttpClient
from app.ingest.chunking import build_chunks
from app.ingest.metadata_extraction import extract_document_metadata
from app.ingest.parsers.docx_parser import parse_docx
from app.ingest.parsers.pdf_parser import parse_pdf
from app.schemas import ReindexResponse


logger = logging.getLogger(__name__)


class DocumentImporter:
    def __init__(self, *, repository, settings, embedding_provider=None) -> None:
        self.repository = repository
        self.settings = settings
        self.embedding_provider = embedding_provider or EmbeddingHttpClient(settings)

    async def reindex_documents(self, force: bool = False, limit: int | None = None) -> ReindexResponse:
        started_at = datetime.now(timezone.utc)
        indexed_documents = 0
        skipped_documents = 0
        ocr_required_documents = 0
        failed_documents = 0

        files = self._discover_files(limit)
        if limit is None:
            existing_paths = {str(file_path.resolve()) for file_path in files}
            delete_missing = getattr(self.repository, "delete_documents_missing_from_disk", None)
            if callable(delete_missing):
                removed_documents = await delete_missing(existing_paths)
                if removed_documents:
                    logger.info("Удалены документы, отсутствующие на диске: %s", removed_documents)
        logger.info("Запущена переиндексация. documents_dir=%s files=%s", self.settings.documents_dir, len(files))
        for file_path in files:
            try:
                file_hash = self._hash_file(file_path)
                existing = await self.repository.get_document_by_path(str(file_path.resolve()))
                if (
                    existing
                    and not force
                    and existing.file_hash == file_hash
                    and existing.status in {DocumentStatus.INDEXED.value, DocumentStatus.OCR_REQUIRED.value}
                ):
                    skipped_documents += 1
                    logger.info("Пропуск без изменений: %s", file_path.name)
                    continue

                parsed_document = self._parse_document(file_path)
                if len(parsed_document.full_text) < 250:
                    await self.repository.replace_document_index(
                        file_path=str(file_path.resolve()),
                        file_name=file_path.name,
                        file_hash=file_hash,
                        file_type=file_path.suffix.lower().lstrip("."),
                        status=DocumentStatus.OCR_REQUIRED.value,
                        metadata_payload=None,
                        chunk_payloads=[],
                        embeddings=None,
                    )
                    ocr_required_documents += 1
                    logger.warning("Документ помечен как OCR_REQUIRED: %s", file_path.name)
                    continue

                metadata = extract_document_metadata(parsed_document.full_text, file_path.name)
                chunks = build_chunks(parsed_document)
                embeddings = await self.embedding_provider.embed_documents([chunk.text for chunk in chunks])
                await self.repository.replace_document_index(
                    file_path=str(file_path.resolve()),
                    file_name=file_path.name,
                    file_hash=file_hash,
                    file_type=file_path.suffix.lower().lstrip("."),
                    status=DocumentStatus.INDEXED.value,
                    metadata_payload=metadata,
                    chunk_payloads=chunks,
                    embeddings=embeddings,
                )
                indexed_documents += 1
                logger.info("Документ проиндексирован: %s chunks=%s", file_path.name, len(chunks))
            except Exception as error:
                failed_documents += 1
                await self.repository.session.rollback()
                logger.exception("Ошибка индексации документа %s: %s", file_path.name, error)
                await self.repository.replace_document_index(
                    file_path=str(file_path.resolve()),
                    file_name=file_path.name,
                    file_hash=self._hash_file(file_path),
                    file_type=file_path.suffix.lower().lstrip("."),
                    status=DocumentStatus.FAILED.value,
                    metadata_payload=None,
                    chunk_payloads=[],
                    embeddings=None,
                )

        finished_at = datetime.now(timezone.utc)
        logger.info(
            "Переиндексация завершена. processed=%s indexed=%s skipped=%s ocr_required=%s failed=%s",
            len(files),
            indexed_documents,
            skipped_documents,
            ocr_required_documents,
            failed_documents,
        )
        return ReindexResponse(
            started_at=started_at,
            finished_at=finished_at,
            processed_documents=len(files),
            indexed_documents=indexed_documents,
            skipped_documents=skipped_documents,
            ocr_required_documents=ocr_required_documents,
            failed_documents=failed_documents,
        )

    def _discover_files(self, limit: int | None) -> list[Path]:
        root = Path(self.settings.documents_dir)
        files = [
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in {".docx", ".pdf"}
        ]
        files.sort()
        if limit is not None:
            return files[:limit]
        return files

    def _parse_document(self, file_path: Path):
        if file_path.suffix.lower() == ".docx":
            return parse_docx(str(file_path))
        if file_path.suffix.lower() == ".pdf":
            return parse_pdf(str(file_path))
        raise ValueError(f"Неподдерживаемый формат: {file_path.suffix}")

    @staticmethod
    def _hash_file(file_path: Path) -> str:
        hasher = hashlib.sha256()
        with file_path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
