from __future__ import annotations

from pathlib import Path

from app.db.repositories import PostgresRepository
from app.schemas import DocumentSummary, HealthResponse, ReindexRequest, ReindexResponse


class AdminService:
    def __init__(
        self,
        *,
        repository: PostgresRepository,
        importer,
        embedding_provider,
        settings,
        database_ok: bool,
    ) -> None:
        self.repository = repository
        self.importer = importer
        self.embedding_provider = embedding_provider
        self.settings = settings
        self.database_ok = database_ok

    async def reindex_documents(self, request: ReindexRequest) -> ReindexResponse:
        return await self.importer.reindex_documents(force=request.force, limit=request.limit)

    async def list_documents(self) -> list[DocumentSummary]:
        return await self.repository.list_documents()

    async def health(self) -> HealthResponse:
        database_ok = await self.repository.healthcheck()
        embedder_ok = await self.embedding_provider.healthcheck()
        documents_dir_exists = Path(self.settings.documents_dir).exists()
        counts = await self.repository.get_document_status_counts() if database_ok else {
            "total": 0,
            "indexed": 0,
            "ocr_required": 0,
            "failed": 0,
        }
        status = "ok" if database_ok and embedder_ok and documents_dir_exists else "degraded"
        return HealthResponse(
            status=status,
            database_ok=database_ok,
            embedder_ok=embedder_ok,
            embedding_service_url=self.settings.embedding_service_url,
            openai_configured=bool(self.settings.openai_api_key),
            openai_model=self.settings.openai_model,
            documents_dir=self.settings.documents_dir,
            documents_dir_exists=documents_dir_exists,
            documents_total=counts["total"],
            indexed_documents=counts["indexed"],
            ocr_required_documents=counts["ocr_required"],
            failed_documents=counts["failed"],
        )
