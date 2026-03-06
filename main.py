import asyncio

from aiogram import Bot, Dispatcher

from bot.background import BackgroundRunner
from bot.handlers import router
from core import Settings, Stats, load_settings


async def main() -> None:
    settings: Settings = load_settings()
    bot = Bot(token=settings.bot_token, parse_mode="HTML")
    dp = Dispatcher()

    stats = Stats()
    runner = BackgroundRunner(
        bot=bot,
        owner_id=settings.owner_id,
        settings=settings,
        stats=stats,
    )

    # Регистрация зависимостей в контексте
    dp.include_router(router)
    dp["stats"] = stats
    dp["runner"] = runner

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

