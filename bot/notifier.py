from __future__ import annotations

from aiogram import Bot

from core.stats import StatsSnapshot


async def notify_hit(bot: Bot, chat_id: int, code: str, discount: float | None) -> None:
    discount_text = f"{discount:.0f} руб." if discount is not None else "неизвестна"
    text = (
        "✅ HIT! Найден рабочий промокод!\n"
        f"Код: {code}\n"
        f"Скидка: {discount_text}"
    )
    await bot.send_message(chat_id, text)


async def notify_dead(bot: Bot, chat_id: int, code: str, reason: str | None) -> None:
    reason_text = reason or "неизвестная причина"
    text = f"❌ {code} - Не работает (Причина: {reason_text})"
    await bot.send_message(chat_id, text)


async def notify_stats(bot: Bot, chat_id: int, snapshot: StatsSnapshot) -> None:
    text = (
        "📊 Статистика проверки промокодов:\n"
        f"Проверено: {snapshot.checked}\n"
        f"Рабочих (HIT): {snapshot.hits}\n"
        f"Нерабочих (DEAD): {snapshot.dead}\n"
        f"Ошибок: {snapshot.errors}\n"
        f"Процент успеха: {snapshot.success_rate:.2f}%"
    )
    await bot.send_message(chat_id, text)

