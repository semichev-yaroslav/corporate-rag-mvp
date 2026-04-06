from types import SimpleNamespace

import pytest

from app.retrieval.hybrid_search import HybridSearchService
from app.schemas import ParsedQuery, SearchCandidate


def make_candidate(candidate_id: str, document_id: str, score: float, file_name: str) -> SearchCandidate:
    return SearchCandidate(
        candidate_id=candidate_id,
        document_id=document_id,
        file_name=file_name,
        text=f"Фрагмент документа {file_name}",
        page_from=1,
        page_to=1,
        section_title=None,
        counterparty_normalized="ООО Ромашка",
        document_number=None,
        doc_type="договор",
        score=score,
    )


class FakeRepository:
    async def search_metadata_candidates(
        self,
        parsed_query: ParsedQuery,
        limit: int,
    ) -> list[SearchCandidate]:
        return [
            make_candidate("a", "doc-1", 3.0, "contract-1.pdf"),
            make_candidate("b", "doc-2", 2.0, "contract-2.pdf"),
        ]

    async def search_text_candidates(self, query_text: str, limit: int) -> list[SearchCandidate]:
        return [
            make_candidate("a", "doc-1", 0.9, "contract-1.pdf"),
            make_candidate("c", "doc-3", 0.8, "contract-3.pdf"),
        ]

    async def search_vector_candidates(
        self,
        query_vector: list[float],
        limit: int,
    ) -> list[SearchCandidate]:
        return [
            make_candidate("a", "doc-1", 0.95, "contract-1.pdf"),
            make_candidate("d", "doc-2", 0.7, "contract-2.pdf"),
        ]


class FakeEmbeddingProvider:
    async def embed_query(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_hybrid_search_fuses_and_limits_documents() -> None:
    service = HybridSearchService(
        repository=FakeRepository(),
        embedding_provider=FakeEmbeddingProvider(),
        settings=SimpleNamespace(retrieval_top_k=4, retrieval_max_documents=2),
    )

    result, parsed_query = await service.search("Был ли договор с ООО Ромашка?")

    assert parsed_query.counterparty == "ООО Ромашка"
    assert result.candidates[0].candidate_id == "a"
    assert len({candidate.document_id for candidate in result.candidates}) <= 2
    assert result.confidence > 0
