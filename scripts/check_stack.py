from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.config import get_settings
from app.db.session import create_engine


async def check_database(database_url: str) -> tuple[bool, str]:
    try:
        from sqlalchemy import text
    except ImportError as error:
        return False, f"sqlalchemy не установлен: {error}"

    engine = create_engine(database_url)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True, "ok"
    except Exception as error:
        return False, str(error)
    finally:
        await engine.dispose()


async def check_embedder(base_url: str) -> tuple[bool, str]:
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{base_url.rstrip('/')}/health")
            response.raise_for_status()
            payload = response.json()
        return True, json.dumps(payload, ensure_ascii=False)
    except Exception as error:
        return False, str(error)


async def main() -> None:
    settings = get_settings()
    database_ok, database_detail = await check_database(settings.database_url)
    embedder_ok, embedder_detail = await check_embedder(settings.embedding_service_url)
    documents_dir = Path(settings.documents_dir)

    payload = {
        "database_ok": database_ok,
        "database_detail": database_detail,
        "embedder_ok": embedder_ok,
        "embedder_detail": embedder_detail,
        "documents_dir": str(documents_dir),
        "documents_dir_exists": documents_dir.exists(),
        "openai_configured": bool(settings.openai_api_key),
        "telegram_configured": bool(settings.telegram_bot_token),
        "openai_model": settings.openai_model,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
