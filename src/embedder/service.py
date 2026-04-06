from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.config import get_settings
from app.logging_config import configure_logging
from embedder.model_loader import get_model_loader
from embedder.schemas import EmbedRequest, EmbedResponse, EmbedderHealthResponse


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    loader = get_model_loader(settings)
    loader.load()
    app.state.loader = loader
    logger.info("Embedder поднят. model_id=%s device=%s", settings.embedding_model_id, loader.device)
    yield
    logger.info("Embedder остановлен.")


settings = get_settings()
configure_logging(settings.log_level)
app = FastAPI(title="Локальный embedder", lifespan=lifespan)


@app.post("/embed", response_model=EmbedResponse)
async def embed(payload: EmbedRequest) -> EmbedResponse:
    settings = get_settings()
    loader = get_model_loader(settings)
    vectors = loader.embed(payload.texts, payload.task_type)
    dimensions = len(vectors[0]) if vectors else settings.embedding_dimensions
    logger.debug("Сгенерированы эмбеддинги. task_type=%s batch=%s", payload.task_type, len(payload.texts))
    return EmbedResponse(
        model_id=settings.embedding_model_id,
        quantization=settings.embedding_quantization,
        dimensions=dimensions,
        vectors=vectors,
    )


@app.get("/health", response_model=EmbedderHealthResponse)
async def health() -> EmbedderHealthResponse:
    settings = get_settings()
    loader = get_model_loader(settings)
    loader.load()
    return EmbedderHealthResponse(
        status="ok",
        model_id=settings.embedding_model_id,
        quantization=settings.embedding_quantization,
        device=loader.device,
    )
