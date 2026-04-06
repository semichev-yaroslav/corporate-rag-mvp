from app.schemas import SearchCandidate
from app.services.answer_formatter import AnswerFormatter, NO_CONFIRMATION_MESSAGE


def test_answer_formatter_returns_no_confirmation_without_candidates() -> None:
    formatter = AnswerFormatter(min_confidence=0.3)
    response = formatter.build_response(
        generated_answer=None,
        candidates=[],
        confidence=0.0,
        latency_ms=10,
    )

    assert response.answer == NO_CONFIRMATION_MESSAGE
    assert response.citations == []


def test_answer_formatter_adds_sources_block() -> None:
    formatter = AnswerFormatter(min_confidence=0.1)
    response = formatter.build_response(
        generated_answer="Да, договор найден.",
        candidates=[
            SearchCandidate(
                candidate_id="1",
                document_id="doc-1",
                file_name="contract.pdf",
                text="Договор заключен с ООО Ромашка до 31.12.2026.",
                page_from=3,
                page_to=3,
                section_title=None,
                counterparty_normalized="ООО Ромашка",
                document_number="12-1",
                doc_type="договор",
                score=0.8,
            )
        ],
        confidence=0.8,
        latency_ms=25,
    )

    assert "Источники:" in response.answer
    assert response.citations[0].file_name == "contract.pdf"
