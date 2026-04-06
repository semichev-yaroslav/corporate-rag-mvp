from __future__ import annotations

from typing import Protocol

from app.schemas import GeneratedAnswer, SearchCandidate


class EmbeddingProvider(Protocol):
    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...


class AnswerGenerator(Protocol):
    async def generate_answer(
        self,
        question: str,
        candidates: list[SearchCandidate],
    ) -> GeneratedAnswer: ...
