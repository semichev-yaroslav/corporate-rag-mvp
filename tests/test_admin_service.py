from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest

from app.schemas import ReindexRequest, ReindexResponse
from app.services.admin_service import AdminService


class FakeRepository:
    def __init__(self, database_ok: bool, counts: dict[str, int]) -> None:
        self._database_ok = database_ok
        self._counts = counts

    async def healthcheck(self) -> bool:
        return self._database_ok

    async def get_document_status_counts(self) -> dict[str, int]:
        return self._counts

    async def list_documents(self) -> list:
        return []


class FakeImporter:
    async def reindex_documents(self, force: bool = False, limit: int | None = None) -> ReindexResponse:
        raise AssertionError("Не должен вызываться в этом тесте")


class FakeEmbeddingProvider:
    def __init__(self, ok: bool) -> None:
        self.ok = ok

    async def healthcheck(self) -> bool:
        return self.ok


@pytest.mark.asyncio
async def test_admin_health_returns_ok_when_stack_is_ready() -> None:
    with TemporaryDirectory() as tmp_dir:
        service = AdminService(
            repository=FakeRepository(
                database_ok=True,
                counts={"total": 10, "indexed": 8, "ocr_required": 1, "failed": 1},
            ),
            importer=FakeImporter(),
            embedding_provider=FakeEmbeddingProvider(ok=True),
            settings=SimpleNamespace(
                embedding_service_url="http://127.0.0.1:8010",
                openai_api_key="key",
                openai_model="gpt-4.1-mini",
                documents_dir=tmp_dir,
            ),
            database_ok=True,
        )

        health = await service.health()

        assert health.status == "ok"
        assert health.database_ok is True
        assert health.embedder_ok is True
        assert health.documents_dir_exists is True
        assert health.documents_total == 10


@pytest.mark.asyncio
async def test_admin_health_returns_degraded_when_documents_dir_missing() -> None:
    missing_dir = str(Path("missing-documents-dir").resolve())
    service = AdminService(
        repository=FakeRepository(
            database_ok=True,
            counts={"total": 0, "indexed": 0, "ocr_required": 0, "failed": 0},
        ),
        importer=FakeImporter(),
        embedding_provider=FakeEmbeddingProvider(ok=False),
        settings=SimpleNamespace(
            embedding_service_url="http://127.0.0.1:8010",
            openai_api_key=None,
            openai_model="gpt-4.1-mini",
            documents_dir=missing_dir,
        ),
        database_ok=True,
    )

    health = await service.health()

    assert health.status == "degraded"
    assert health.embedder_ok is False
    assert health.documents_dir_exists is False
