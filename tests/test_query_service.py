from types import SimpleNamespace

import pytest

from app.schemas import ConversationMessage, GeneratedAnswer, ParsedQuery, QueryRequest, SearchCandidate, SearchResult
from app.services.answer_formatter import AnswerFormatter
from app.services.query_service import QueryService


class FakeRepository:
    def __init__(self) -> None:
        self.logged = None
        self.history_calls: list[tuple[str, int]] = []

    async def is_user_allowed(self, telegram_user_id: str) -> bool | None:
        return True

    async def get_recent_conversation_messages(
        self,
        telegram_user_id: str,
        limit_messages: int,
    ) -> list[ConversationMessage]:
        self.history_calls.append((telegram_user_id, limit_messages))
        return [
            ConversationMessage(role="user", text="Первый вопрос"),
            ConversationMessage(role="assistant", text="Первый ответ"),
            ConversationMessage(role="user", text="Второй вопрос"),
            ConversationMessage(role="assistant", text="Второй ответ"),
        ]

    async def log_query(self, **kwargs) -> None:
        self.logged = kwargs


class FakeHybridSearch:
    def __init__(self) -> None:
        self.last_question = None

    async def search(self, text: str) -> tuple[SearchResult, ParsedQuery]:
        self.last_question = text
        candidates = [
            SearchCandidate(
                candidate_id="chunk-1",
                document_id="doc-1",
                file_name="dogovor.docx",
                text="Договор действует до 31.12.2026.",
                page_from=1,
                page_to=1,
                section_title=None,
                counterparty_normalized="ООО Ромашка",
                document_number="123",
                doc_type="Договор",
                score=0.99,
                source_scores={"text": 0.99},
            )
        ]
        return SearchResult(candidates=candidates, confidence=0.99), ParsedQuery(
            original_text=text,
            normalized_text=text.lower(),
        )


class FakeGenerator:
    def __init__(self) -> None:
        self.last_call = None

    async def generate_answer(
        self,
        question: str,
        candidates: list[SearchCandidate],
        conversation_history: list[ConversationMessage] | None = None,
    ) -> GeneratedAnswer:
        self.last_call = {
            "question": question,
            "candidates": candidates,
            "conversation_history": conversation_history,
        }
        return GeneratedAnswer(text="Ответ по документу.", model="gpt-4.1-mini")


@pytest.mark.asyncio
async def test_query_service_passes_recent_conversation_to_generator() -> None:
    repository = FakeRepository()
    generator = FakeGenerator()
    hybrid_search = FakeHybridSearch()
    service = QueryService(
        repository=repository,
        settings=SimpleNamespace(
            allowed_telegram_user_ids=[],
            require_allowlist=False,
            conversation_history_messages=10,
        ),
        hybrid_search=hybrid_search,
        generator=generator,
        formatter=AnswerFormatter(min_confidence=0.25),
    )

    response = await service.handle_query(
        QueryRequest(
            user_id="42",
            chat_id="42",
            text="Когда заканчивается договор?",
        )
    )

    assert repository.history_calls == [("42", 10)]
    assert generator.last_call is not None
    assert hybrid_search.last_question is not None
    assert [message.text for message in generator.last_call["conversation_history"]] == [
        "Первый вопрос",
        "Первый ответ",
        "Второй вопрос",
        "Второй ответ",
    ]
    assert response.answer.startswith("Ответ по документу.")
    assert repository.logged is not None


@pytest.mark.asyncio
async def test_query_service_expands_follow_up_question_for_retrieval() -> None:
    repository = FakeRepository()
    generator = FakeGenerator()
    hybrid_search = FakeHybridSearch()
    service = QueryService(
        repository=repository,
        settings=SimpleNamespace(
            allowed_telegram_user_ids=[],
            require_allowlist=False,
            conversation_history_messages=10,
        ),
        hybrid_search=hybrid_search,
        generator=generator,
        formatter=AnswerFormatter(min_confidence=0.25),
    )

    await service.handle_query(
        QueryRequest(
            user_id="42",
            chat_id="42",
            text="А когда он заканчивается?",
        )
    )

    assert hybrid_search.last_question is not None
    assert "Предыдущий вопрос: Первый вопрос" in hybrid_search.last_question
    assert "Предыдущий вопрос: Второй вопрос" in hybrid_search.last_question
    assert hybrid_search.last_question.endswith("Текущий вопрос: А когда он заканчивается?")
