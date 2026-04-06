from __future__ import annotations

import logging
from time import perf_counter

from app.db.repositories import PostgresRepository
from app.retrieval.query_parser import parse_query
from app.schemas import ConversationMessage, QueryRequest, QueryResponse
from app.services.answer_formatter import AnswerFormatter


logger = logging.getLogger(__name__)


class PermissionDeniedError(RuntimeError):
    pass


class QueryService:
    def __init__(
        self,
        *,
        repository: PostgresRepository,
        settings,
        hybrid_search,
        generator,
        formatter: AnswerFormatter,
    ) -> None:
        self.repository = repository
        self.settings = settings
        self.hybrid_search = hybrid_search
        self.generator = generator
        self.formatter = formatter

    async def handle_query(self, request: QueryRequest) -> QueryResponse:
        started = perf_counter()
        await self._ensure_user_allowed(request.user_id)
        logger.info("Получен запрос trace_id=%s user_id=%s", request.trace_id, request.user_id)
        conversation_history = await self.repository.get_recent_conversation_messages(
            request.user_id,
            self.settings.conversation_history_messages,
        )
        retrieval_question = self._build_retrieval_question(request.text, conversation_history)
        if retrieval_question != request.text:
            logger.info("Для retrieval использован расширенный контекст trace_id=%s", request.trace_id)
        search_result, _ = await self.hybrid_search.search(retrieval_question)
        generated_answer = None

        if search_result.candidates:
            generated = await self.generator.generate_answer(
                request.text,
                search_result.candidates,
                conversation_history=conversation_history,
            )
            generated_answer = generated.text

        latency_ms = int((perf_counter() - started) * 1000)
        response = self.formatter.build_response(
            generated_answer=generated_answer,
            candidates=search_result.candidates,
            confidence=search_result.confidence,
            latency_ms=latency_ms,
        )
        await self.repository.log_query(
            telegram_user_id=request.user_id,
            question=request.text,
            normalized_question=parse_query(request.text).normalized_text,
            answer=response.answer,
            confidence=response.confidence,
            latency_ms=response.latency_ms,
        )
        logger.info(
            "Запрос обработан trace_id=%s candidates=%s confidence=%.4f latency_ms=%s",
            request.trace_id,
            len(search_result.candidates),
            response.confidence,
            response.latency_ms,
        )
        return response

    async def _ensure_user_allowed(self, user_id: str) -> None:
        env_allowlist = set(self.settings.allowed_telegram_user_ids)
        if user_id in env_allowlist:
            return

        db_flag = await self.repository.is_user_allowed(user_id)
        if db_flag is True:
            return

        if self.settings.require_allowlist:
            raise PermissionDeniedError("Пользователь не входит в allowlist.")

    def _build_retrieval_question(
        self,
        question: str,
        conversation_history: list[ConversationMessage],
    ) -> str:
        parsed_query = parse_query(question)
        if parsed_query.counterparty or parsed_query.document_number:
            return question

        if not self._looks_like_follow_up(parsed_query.normalized_text):
            return question

        recent_user_messages = [
            message.text.strip()
            for message in conversation_history
            if message.role == "user" and message.text.strip()
        ]
        if not recent_user_messages:
            return question

        context_lines = [f"Предыдущий вопрос: {message}" for message in recent_user_messages[-3:]]
        context_lines.append(f"Текущий вопрос: {question}")
        return "\n".join(context_lines)

    @staticmethod
    def _looks_like_follow_up(normalized_question: str) -> bool:
        follow_up_markers = (
            " а ",
            "он",
            "она",
            "оно",
            "его",
            "её",
            "ее",
            "их",
            "этот",
            "эта",
            "это",
            "этому",
            "этого",
            "этой",
            "срок",
            "сумма",
            "стоимость",
            "номер",
            "дата",
            "когда заканч",
            "до какого",
        )
        words = normalized_question.split()
        if len(words) <= 6:
            return True
        return any(marker in normalized_question for marker in follow_up_markers)
