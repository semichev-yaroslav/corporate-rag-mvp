from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


def create_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, future=True, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def apply_sql_migrations(engine: AsyncEngine, migrations_dir: Path) -> None:
    migration_files = sorted(migrations_dir.glob("*.sql"))
    if not migration_files:
        return

    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        result = await connection.execute(text("SELECT version FROM schema_migrations"))
        applied_versions = {row[0] for row in result}

        for file_path in migration_files:
            if file_path.name in applied_versions:
                continue
            sql = file_path.read_text(encoding="utf-8")
            for statement in [part.strip() for part in sql.split(";") if part.strip()]:
                await connection.execute(text(statement))
            await connection.execute(
                text("INSERT INTO schema_migrations(version) VALUES (:version)"),
                {"version": file_path.name},
            )
