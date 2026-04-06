from __future__ import annotations

from collections import OrderedDict, defaultdict
import logging

from app.retrieval.query_parser import parse_query
from app.retrieval.rerank import rerank_candidates
from app.schemas import ParsedQuery, SearchCandidate, SearchResult


logger = logging.getLogger(__name__)


class HybridSearchService:
    def __init__(self, *, repository, embedding_provider, settings) -> None:
        self.repository = repository
        self.embedding_provider = embedding_provider
        self.settings = settings

    async def search(self, question: str) -> tuple[SearchResult, ParsedQuery]:
        parsed_query = parse_query(question)
        logger.debug("Парсинг запроса завершен. type=%s counterparty=%s", parsed_query.question_type, parsed_query.counterparty)
        metadata_candidates = await self.repository.search_metadata_candidates(
            parsed_query,
            limit=self.settings.retrieval_top_k,
        )
        text_candidates = await self.repository.search_text_candidates(
            question,
            limit=self.settings.retrieval_top_k * 2,
        )
        query_vector = await self.embedding_provider.embed_query(question)
        vector_candidates = await self.repository.search_vector_candidates(
            query_vector,
            limit=self.settings.retrieval_top_k * 2,
        )

        fused = self._fuse_rankings(
            metadata_candidates,
            text_candidates,
            vector_candidates,
        )
        reranked = rerank_candidates(list(fused.values()), parsed_query)
        selected = self._diversify(reranked)
        confidence = self._estimate_confidence(selected)
        logger.info(
            "Hybrid search завершен. metadata=%s text=%s vector=%s selected=%s confidence=%.4f",
            len(metadata_candidates),
            len(text_candidates),
            len(vector_candidates),
            len(selected),
            confidence,
        )
        return SearchResult(candidates=selected, confidence=confidence), parsed_query

    def _fuse_rankings(
        self,
        metadata_candidates: list[SearchCandidate],
        text_candidates: list[SearchCandidate],
        vector_candidates: list[SearchCandidate],
    ) -> OrderedDict[str, SearchCandidate]:
        weights = {"metadata": 1.3, "text": 1.0, "vector": 1.1}
        fused_scores: defaultdict[str, float] = defaultdict(float)
        candidates: dict[str, SearchCandidate] = {}

        for source, ranking in (
            ("metadata", metadata_candidates),
            ("text", text_candidates),
            ("vector", vector_candidates),
        ):
            weight = weights[source]
            for rank, candidate in enumerate(ranking, start=1):
                fused_scores[candidate.candidate_id] += weight / (60 + rank)
                if candidate.candidate_id not in candidates:
                    candidates[candidate.candidate_id] = candidate
                merged_scores = dict(candidates[candidate.candidate_id].source_scores)
                merged_scores[source] = candidate.score
                candidates[candidate.candidate_id] = candidates[candidate.candidate_id].model_copy(
                    update={"source_scores": merged_scores}
                )

        sorted_items = sorted(
            fused_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        ordered: OrderedDict[str, SearchCandidate] = OrderedDict()
        for candidate_id, fused_score in sorted_items:
            ordered[candidate_id] = candidates[candidate_id].model_copy(update={"score": fused_score})
        return ordered

    def _diversify(self, candidates: list[SearchCandidate]) -> list[SearchCandidate]:
        selected: list[SearchCandidate] = []
        documents_seen: dict[str, int] = defaultdict(int)
        for candidate in candidates:
            if len(selected) >= self.settings.retrieval_top_k:
                break
            if (
                candidate.document_id not in documents_seen
                and len(documents_seen) >= self.settings.retrieval_max_documents
            ):
                continue
            if documents_seen[candidate.document_id] >= 3:
                continue
            selected.append(candidate)
            documents_seen[candidate.document_id] += 1
        return selected

    @staticmethod
    def _estimate_confidence(candidates: list[SearchCandidate]) -> float:
        if not candidates:
            return 0.0
        top_score = candidates[0].score
        evidence_bonus = min(0.2, len(candidates) * 0.03)
        return round(min(0.99, top_score * 6 + evidence_bonus), 4)
