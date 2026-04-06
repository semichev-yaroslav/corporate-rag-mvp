from __future__ import annotations

import logging

from app.schemas import ConversationMessage, GeneratedAnswer, SearchCandidate


logger = logging.getLogger(__name__)


class OpenAIResponseGenerator:
    def __init__(self, settings) -> None:
        self.settings = settings

    async def generate_answer(
        self,
        question: str,
        candidates: list[SearchCandidate],
        conversation_history: list[ConversationMessage] | None = None,
    ) -> GeneratedAnswer:
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI API key не настроен.")

        try:
            from openai import AsyncOpenAI
        except ImportError as error:
            raise RuntimeError("Пакет openai не установлен.") from error

        client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        sources = []
        for index, candidate in enumerate(candidates[:6], start=1):
            page_label = ""
            if candidate.page_from and candidate.page_to and candidate.page_from != candidate.page_to:
                page_label = f"стр. {candidate.page_from}-{candidate.page_to}"
            elif candidate.page_from:
                page_label = f"стр. {candidate.page_from}"
            elif candidate.section_title:
                page_label = f"раздел {candidate.section_title}"
            sources.append(
                f"[{index}] {candidate.file_name} ({page_label or 'без страницы'}): "
                f"{' '.join(candidate.text.split())[:1200]}"
            )
        user_prompt = self._build_user_prompt(question, sources, conversation_history or [])

        try:
            response = await client.responses.create(
                model=self.settings.openai_model,
                input=[
                    {
                        "role": "system",
                        "content": [
                            {
                                "type": "input_text",
                                "text": (
                                    "Ты отвечаешь только по переданным источникам. "
                                    "Не выдумывай факты, отвечай кратко на русском в 1-2 предложениях. "
                                    "Если данных недостаточно, напиши: НЕ ХВАТАЕТ ДАННЫХ. "
                                    "Историю переписки используй только как контекст диалога, "
                                    "но подтверждай факты исключительно по текущим источникам."
                                ),
                            }
                        ],
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": user_prompt,
                            }
                        ],
                    },
                ],
            )
        except Exception as error:
            logger.warning("OpenAI Responses API вернул ошибку: %s", error)
            raise RuntimeError("OpenAI недоступен или вернул ошибку при генерации ответа.") from error
        answer_text = (response.output_text or "").strip()
        if answer_text.upper().startswith("НЕ ХВАТАЕТ ДАННЫХ"):
            answer_text = ""
        return GeneratedAnswer(text=answer_text, model=self.settings.openai_model)

    def _build_user_prompt(
        self,
        question: str,
        sources: list[str],
        conversation_history: list[ConversationMessage],
    ) -> str:
        parts: list[str] = []
        history_block = self._format_history(conversation_history)
        if history_block:
            parts.append(f"Последние сообщения переписки:\n{history_block}")
        parts.append(f"Текущий вопрос:\n{question}")
        parts.append("Источники:\n" + "\n\n".join(sources))
        return "\n\n".join(parts)

    def _format_history(self, conversation_history: list[ConversationMessage]) -> str:
        formatted_messages: list[str] = []
        for message in conversation_history:
            normalized = self._normalize_history_text(message.text)
            if not normalized:
                continue
            speaker = "Пользователь" if message.role == "user" else "Ассистент"
            formatted_messages.append(f"{speaker}: {normalized}")
        return "\n".join(formatted_messages)

    @staticmethod
    def _normalize_history_text(text: str, limit: int = 800) -> str:
        cleaned = text.split("\n\nИсточники:\n", maxsplit=1)[0]
        compact = " ".join(cleaned.split()).strip()
        if len(compact) <= limit:
            return compact
        return compact[: limit - 1].rstrip() + "…"
