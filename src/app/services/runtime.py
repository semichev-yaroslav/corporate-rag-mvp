from __future__ import annotations

from pathlib import Path

from fastapi import Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.repositories import PostgresRepository
from app.db.session import apply_sql_migrations, create_engine, create_session_factory
from app.ingest.importer import DocumentImporter
from app.providers.embedding_client import EmbeddingHttpClient
from app.providers.openai_generator import OpenAIResponseGenerator
from app.retrieval.hybrid_search import HybridSearchService
from app.services.admin_service import AdminService
from app.services.answer_formatter import AnswerFormatter
from app.services.query_service import QueryService


engine = None
session_factory = None


def get_engine(settings: Settings):
    global engine
    if engine is None:
        engine = create_engine(settings.database_url)
    return engine


def get_session_factory(settings: Settings):
    global session_factory
    if session_factory is None:
        session_factory = create_session_factory(get_engine(settings))
    return session_factory


async def get_session(settings: Settings = Depends(get_settings)) -> AsyncSession:
    factory = get_session_factory(settings)
    async with factory() as session:
        yield session


async def initialize_database(settings: Settings) -> bool:
    db_engine = get_engine(settings)
    try:
        if settings.auto_apply_db_migrations:
            migrations_dir = Path(__file__).resolve().parents[1] / "db" / "migrations"
            await apply_sql_migrations(db_engine, migrations_dir)
        async with db_engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def get_query_service(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> QueryService:
    repository = PostgresRepository(session)
    embedder = EmbeddingHttpClient(settings)
    hybrid_search = HybridSearchService(repository=repository, embedding_provider=embedder, settings=settings)
    generator = OpenAIResponseGenerator(settings)
    formatter = AnswerFormatter(min_confidence=settings.retrieval_min_confidence)
    return QueryService(
        repository=repository,
        settings=settings,
        hybrid_search=hybrid_search,
        generator=generator,
        formatter=formatter,
    )


def get_admin_service(
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AdminService:
    repository = PostgresRepository(session)
    embedding_provider = EmbeddingHttpClient(settings)
    importer = DocumentImporter(
        repository=repository,
        settings=settings,
        embedding_provider=embedding_provider,
    )
    return AdminService(
        repository=repository,
        importer=importer,
        embedding_provider=embedding_provider,
        settings=settings,
        database_ok=bool(getattr(request.app.state, "database_ok", False)) if request else False,
    )
