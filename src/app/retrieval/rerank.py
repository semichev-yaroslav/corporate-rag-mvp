from __future__ import annotations

from app.schemas import ParsedQuery, SearchCandidate


def rerank_candidates(candidates: list[SearchCandidate], parsed_query: ParsedQuery) -> list[SearchCandidate]:
    reranked: list[SearchCandidate] = []
    for candidate in candidates:
        score = candidate.score
        if parsed_query.counterparty and candidate.counterparty_normalized:
            if parsed_query.counterparty == candidate.counterparty_normalized:
                score += 0.25
            elif parsed_query.counterparty.lower() in candidate.counterparty_normalized.lower():
                score += 0.15
        if parsed_query.document_number and candidate.document_number:
            if parsed_query.document_number == candidate.document_number:
                score += 0.2
        if parsed_query.question_type == "amount" and "сумм" in candidate.text.lower():
            score += 0.05
        if parsed_query.question_type == "end_date" and any(
            token in candidate.text.lower() for token in ("действует до", "оканчивается", "срок")
        ):
            score += 0.05
        reranked.append(candidate.model_copy(update={"score": round(score, 6)}))

    reranked.sort(key=lambda item: item.score, reverse=True)
    return reranked
