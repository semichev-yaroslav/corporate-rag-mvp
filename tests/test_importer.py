from pathlib import Path
from types import SimpleNamespace

import pytest

from app.db.models import DocumentStatus
from app.ingest.importer import DocumentImporter
from app.schemas import DocumentFragment, ParsedDocument


class FakeSession:
    def __init__(self) -> None:
        self.rolled_back = False

    async def rollback(self) -> None:
        self.rolled_back = True


class FakeRepository:
    def __init__(self) -> None:
        self.session = FakeSession()
        self.records: list[dict] = []

    async def get_document_by_path(self, file_path: str):
        return None

    async def replace_document_index(self, **kwargs):
        self.records.append(kwargs)
        return "doc-1"


class FailingEmbeddingProvider:
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("embedder down")


class DummyEmbeddingProvider:
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2] for _ in texts]


@pytest.mark.asyncio
async def test_importer_marks_short_document_as_ocr_required(tmp_path: Path) -> None:
    file_path = tmp_path / "scan.pdf"
    file_path.write_bytes(b"fake")
    repository = FakeRepository()
    importer = DocumentImporter(
        repository=repository,
        settings=SimpleNamespace(documents_dir=str(tmp_path)),
        embedding_provider=DummyEmbeddingProvider(),
    )
    importer._hash_file = lambda _: "hash-short"
    importer._parse_document = lambda _: ParsedDocument(
        file_path=str(file_path),
        file_name=file_path.name,
        file_type="pdf",
        fragments=[DocumentFragment(text="очень мало текста", page_from=1, page_to=1, order=1)],
    )

    result = await importer.reindex_documents()

    assert result.ocr_required_documents == 1
    assert repository.records[0]["status"] == DocumentStatus.OCR_REQUIRED.value


@pytest.mark.asyncio
async def test_importer_marks_document_failed_when_embedding_service_fails(tmp_path: Path) -> None:
    file_path = tmp_path / "contract.docx"
    file_path.write_bytes(b"fake")
    repository = FakeRepository()
    importer = DocumentImporter(
        repository=repository,
        settings=SimpleNamespace(documents_dir=str(tmp_path)),
        embedding_provider=FailingEmbeddingProvider(),
    )
    importer._hash_file = lambda _: "hash-failed"
    importer._parse_document = lambda _: ParsedDocument(
        file_path=str(file_path),
        file_name=file_path.name,
        file_type="docx",
        fragments=[DocumentFragment(text="слово " * 400, page_from=None, page_to=None, order=1)],
    )

    result = await importer.reindex_documents()

    assert result.failed_documents == 1
    assert repository.session.rolled_back is True
    assert repository.records[-1]["status"] == DocumentStatus.FAILED.value
