from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.config import get_settings
from app.db.repositories import PostgresRepository
from app.services.runtime import get_engine, get_session_factory, initialize_database
from app.ingest.importer import DocumentImporter


async def reindex(force: bool, limit: int | None) -> None:
    settings = get_settings()
    await initialize_database(settings)
    session_factory = get_session_factory(settings)
    async with session_factory() as session:
        repository = PostgresRepository(session)
        importer = DocumentImporter(repository=repository, settings=settings)
        result = await importer.reindex_documents(force=force, limit=limit)
        print(result.model_dump_json(indent=2, exclude_none=True))
    await get_engine(settings).dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ручной реиндекс архива документов.")
    parser.add_argument("--force", action="store_true", help="Переиндексировать даже неизмененные файлы.")
    parser.add_argument("--limit", type=int, default=None, help="Ограничить число документов.")
    args = parser.parse_args()
    asyncio.run(reindex(force=args.force, limit=args.limit))


if __name__ == "__main__":
    main()
