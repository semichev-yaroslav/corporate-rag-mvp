from __future__ import annotations

from uuid import uuid4

import httpx
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message


def build_router(settings) -> Router:
    router = Router()
    backend_url = settings.api_base_url.rstrip("/")
    operator_ids = set(settings.operator_telegram_user_ids)

    async def call_query_api(message: Message, text: str) -> str:
        payload = {
            "user_id": str(message.from_user.id),
            "chat_id": str(message.chat.id),
            "text": text,
            "trace_id": str(uuid4()),
        }
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(f"{backend_url}/api/query", json=payload)
            response.raise_for_status()
            return response.json()["answer"]

    async def call_admin_api(path: str, user_id: str, method: str = "GET", json: dict | None = None) -> dict:
        headers = {"X-Operator-Id": user_id}
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.request(
                method,
                f"{backend_url}{path}",
                headers=headers,
                json=json,
            )
            response.raise_for_status()
            return response.json()

    @router.message(CommandStart())
    async def start_handler(message: Message) -> None:
        await message.answer(
            "Бот ищет ответы по локальному архиву документов.\n"
            "Доступные команды: /help, /status, /reindex."
        )

    @router.message(Command("help"))
    async def help_handler(message: Message) -> None:
        await message.answer(
            "Отправьте вопрос о договоре обычным текстом.\n"
            "Примеры:\n"
            "1. Был ли у нас договор с ООО Ромашка?\n"
            "2. Когда заканчивается договор с ООО Ромашка?\n"
            "3. На какую сумму у нас договор с ООО Тест?"
        )

    @router.message(Command("status"))
    async def status_handler(message: Message) -> None:
        user_id = str(message.from_user.id)
        if user_id not in operator_ids:
            await message.answer("Команда доступна только оператору.")
            return
        try:
            payload = await call_admin_api("/api/admin/health", user_id=user_id)
        except Exception as error:
            await message.answer(f"Не удалось получить статус: {error}")
            return
        await message.answer(
            "Статус API: {status}\n"
            "База данных: {db}\n"
            "Embedder: {embedder}\n"
            "Документы: {docs}\n"
            "Папка доступна: {docs_exists}\n"
            "Индекс: всего {total}, indexed {indexed}, ocr {ocr}, failed {failed}".format(
                status=payload["status"],
                db="ok" if payload["database_ok"] else "ошибка",
                embedder="ok" if payload["embedder_ok"] else "ошибка",
                docs=payload["documents_dir"],
                docs_exists="да" if payload["documents_dir_exists"] else "нет",
                total=payload["documents_total"],
                indexed=payload["indexed_documents"],
                ocr=payload["ocr_required_documents"],
                failed=payload["failed_documents"],
            )
        )

    @router.message(Command("reindex"))
    async def reindex_handler(message: Message) -> None:
        user_id = str(message.from_user.id)
        if user_id not in operator_ids:
            await message.answer("Команда доступна только оператору.")
            return
        await message.answer("Запускаю переиндексацию. Это может занять несколько минут.")
        try:
            payload = await call_admin_api(
                "/api/admin/reindex",
                user_id=user_id,
                method="POST",
                json={"force": False, "limit": None},
            )
        except Exception as error:
            await message.answer(f"Переиндексация завершилась ошибкой: {error}")
            return
        await message.answer(
            "Готово.\n"
            f"Обработано: {payload['processed_documents']}\n"
            f"Проиндексировано: {payload['indexed_documents']}\n"
            f"OCR_REQUIRED: {payload['ocr_required_documents']}\n"
            f"Ошибки: {payload['failed_documents']}"
        )

    @router.message(~F.chat.type.in_({"private"}))
    async def reject_non_private(message: Message) -> None:
        await message.answer("В MVP поддерживается только личный чат.")

    @router.message(F.text)
    async def query_handler(message: Message) -> None:
        try:
            answer = await call_query_api(message, message.text)
        except httpx.HTTPStatusError as error:
            detail = error.response.text
            await message.answer(f"Запрос не выполнен: {detail}")
            return
        except Exception as error:
            await message.answer(f"Сервис недоступен: {error}")
            return
        await message.answer(answer)

    return router
