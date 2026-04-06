from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher

from app.bot.handlers import build_router
from app.config import get_settings


async def start_polling() -> None:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise RuntimeError("APP_TELEGRAM_BOT_TOKEN не настроен.")

    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(build_router(settings))
    await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())


def main() -> None:
    asyncio.run(start_polling())


if __name__ == "__main__":
    main()
