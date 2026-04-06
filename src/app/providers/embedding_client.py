from __future__ import annotations

import logging

import httpx


logger = logging.getLogger(__name__)


class EmbeddingHttpClient:
    def __init__(self, settings) -> None:
        self.base_url = settings.embedding_service_url.rstrip("/")

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._embed(texts, task_type="document")

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self._embed([text], task_type="query")
        return vectors[0]

    async def healthcheck(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()
            return True
        except Exception as error:
            logger.warning("Проверка embedder health завершилась ошибкой: %s", error)
            return False

    async def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        if not texts:
            return []
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{self.base_url}/embed",
                    json={"texts": texts, "task_type": task_type},
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as error:
            logger.warning(
                "Embedding service вернул ошибку. status=%s body=%s",
                error.response.status_code,
                error.response.text,
            )
            raise RuntimeError("Embedding service вернул ошибку и не смог обработать запрос.") from error
        except httpx.RequestError as error:
            logger.warning("Embedding service недоступен: %s", error)
            raise RuntimeError("Embedding service недоступен. Проверьте локальный embedder.") from error
        vectors = payload.get("vectors", [])
        if len(vectors) != len(texts):
            logger.warning(
                "Embedding service вернул неожиданный размер ответа. expected=%s actual=%s",
                len(texts),
                len(vectors),
            )
            raise RuntimeError("Embedding service вернул неожиданный размер ответа.")
        return vectors
