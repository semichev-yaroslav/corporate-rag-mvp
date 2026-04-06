from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.api.admin import router as admin_router
from app.api.query import router as query_router
from app.config import get_settings
from app.logging_config import configure_logging
from app.services.runtime import get_engine, initialize_database


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.database_ok = await initialize_database(settings)
    logger.info("Приложение запущено. database_ok=%s", app.state.database_ok)
    yield
    engine = get_engine(settings)
    await engine.dispose()
    logger.info("Приложение остановлено.")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    application = FastAPI(title=settings.app_name, lifespan=lifespan)
    application.include_router(query_router)
    application.include_router(admin_router)
    return application


app = create_app()
