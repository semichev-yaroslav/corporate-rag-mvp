from __future__ import annotations

from collections import defaultdict

from app.schemas import Citation, MatchedDocument, QueryResponse, SearchCandidate


NO_CONFIRMATION_MESSAGE = (
    "В проиндексированных документах надежного подтверждения не найдено. "
    "Уточните контрагента или номер документа."
)


class AnswerFormatter:
    def __init__(self, min_confidence: float) -> None:
        self.min_confidence = min_confidence

    def build_response(
        self,
        *,
        generated_answer: str | None,
        candidates: list[SearchCandidate],
        confidence: float,
        latency_ms: int,
    ) -> QueryResponse:
        if not candidates or confidence < self.min_confidence or not generated_answer:
            return QueryResponse(
                answer=NO_CONFIRMATION_MESSAGE,
                confidence=round(confidence, 4),
                citations=[],
                matched_documents=[],
                latency_ms=latency_ms,
            )

        citations = self._build_citations(candidates)
        matched_documents = self._build_matched_documents(candidates)
        answer_text = generated_answer.strip()
        answer = f"{answer_text}\n\nИсточники:\n{self._format_sources(citations)}"
        return QueryResponse(
            answer=answer,
            confidence=round(confidence, 4),
            citations=citations,
            matched_documents=matched_documents,
            latency_ms=latency_ms,
        )

    def _build_citations(self, candidates: list[SearchCandidate]) -> list[Citation]:
        citations: list[Citation] = []
        seen: set[tuple[str, str]] = set()
        for candidate in candidates:
            key = (candidate.document_id, candidate.text[:120])
            if key in seen:
                continue
            seen.add(key)
            citations.append(
                Citation(
                    document_id=candidate.document_id,
                    file_name=candidate.file_name,
                    page_from=candidate.page_from,
                    page_to=candidate.page_to,
                    section_title=candidate.section_title,
                    snippet=self._truncate(candidate.text),
                )
            )
            if len(citations) >= 3:
                break
        return citations

    def _build_matched_documents(self, candidates: list[SearchCandidate]) -> list[MatchedDocument]:
        grouped_scores: dict[str, list[float]] = defaultdict(list)
        file_names: dict[str, str] = {}
        for candidate in candidates:
            grouped_scores[candidate.document_id].append(candidate.score)
            file_names[candidate.document_id] = candidate.file_name

        matched_documents = [
            MatchedDocument(
                document_id=document_id,
                file_name=file_names[document_id],
                score=round(max(scores), 4),
                matched_chunks=len(scores),
            )
            for document_id, scores in grouped_scores.items()
        ]
        matched_documents.sort(key=lambda item: item.score, reverse=True)
        return matched_documents[:3]

    def _format_sources(self, citations: list[Citation]) -> str:
        lines = []
        for index, citation in enumerate(citations, start=1):
            page_label = ""
            if citation.page_from and citation.page_to and citation.page_from != citation.page_to:
                page_label = f"стр. {citation.page_from}-{citation.page_to}"
            elif citation.page_from:
                page_label = f"стр. {citation.page_from}"
            elif citation.section_title:
                page_label = f"раздел {citation.section_title}"
            lines.append(f"{index}. {citation.file_name} ({page_label or 'без страницы'}) — {citation.snippet}")
        return "\n".join(lines)

    @staticmethod
    def _truncate(text: str, limit: int = 220) -> str:
        compact = " ".join(text.split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 1].rstrip() + "…"
