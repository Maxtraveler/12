from __future__ import annotations

from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from core.stats import Stats

from .background import BackgroundRunner
from .states import PromoStates


router = Router()


def _mode_keyboard() -> ReplyKeyboardBuilder:
    kb = ReplyKeyboardBuilder()
    kb.button(text="Маска")
    kb.button(text="Файл")
    kb.button(text="Одиночный код")
    kb.adjust(3)
    return kb


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, bot: Bot) -> None:
    await state.clear()
    await message.answer(
        "Привет! Я бот для проверки промокодов.\n"
        "Используй /start_check, чтобы начать проверку.",
    )


@router.message(Command("start_check"))
async def cmd_start_check(message: Message, state: FSMContext) -> None:
    kb = _mode_keyboard()
    await state.set_state(PromoStates.choosing_mode)
    await message.answer(
        "Выбери режим работы:\n"
        "• Маска — генерация по маске (например, KL6XXXXX)\n"
        "• Файл — загрузка файла с кодами\n"
        "• Одиночный код — проверка одного кода",
        reply_markup=kb.as_markup(resize_keyboard=True, one_time_keyboard=True),
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message, stats: Stats) -> None:
    snapshot = await stats.snapshot()
    text = (
        "📊 Текущая статистика:\n"
        f"Проверено: {snapshot.checked}\n"
        f"Рабочих (HIT): {snapshot.hits}\n"
        f"Нерабочих (DEAD): {snapshot.dead}\n"
        f"Ошибок: {snapshot.errors}\n"
        f"Процент успеха: {snapshot.success_rate:.2f}%"
    )
    await message.answer(text)


@router.message(PromoStates.choosing_mode, F.text == "Маска")
async def choose_mask(message: Message, state: FSMContext) -> None:
    await state.set_state(PromoStates.waiting_mask)
    await message.answer("Введи маску для генерации (например, KL6XXXXX).")


@router.message(PromoStates.choosing_mode, F.text == "Файл")
async def choose_file(message: Message, state: FSMContext) -> None:
    await state.set_state(PromoStates.waiting_file)
    await message.answer("Отправь файл с промокодами (по одному коду в строке).")


@router.message(PromoStates.choosing_mode, F.text == "Одиночный код")
async def choose_single_code(message: Message, state: FSMContext) -> None:
    await state.set_state(PromoStates.waiting_single_code)
    await message.answer("Введи один промокод для проверки.")


@router.message(PromoStates.waiting_mask)
async def handle_mask(message: Message, state: FSMContext, runner: BackgroundRunner) -> None:
    mask = (message.text or "").strip()
    if not mask:
        await message.answer("Маска не должна быть пустой. Попробуй ещё раз.")
        return

    await state.clear()
    await message.answer(f"Запускаю проверку для маски: {mask}")
    await runner.start_with_mask(mask)


@router.message(PromoStates.waiting_single_code)
async def handle_single_code(message: Message, state: FSMContext, runner: BackgroundRunner) -> None:
    code = (message.text or "").strip()
    if not code:
        await message.answer("Код не должен быть пустым. Попробуй ещё раз.")
        return

    await state.clear()
    await message.answer(f"Проверяю промокод: {code}")
    await runner.start_with_single_code(code)


@router.message(PromoStates.waiting_file, F.document)
async def handle_file(message: Message, state: FSMContext, runner: BackgroundRunner, bot: Bot) -> None:
    document = message.document
    if document is None:
        await message.answer("Пожалуйста, отправь именно файл с промокодами.")
        return

    temp_dir = Path("uploads")
    temp_dir.mkdir(parents=True, exist_ok=True)
    file_path = temp_dir / f"{document.file_unique_id}.txt"

    file = await bot.get_file(document.file_id)
    await bot.download_file(file.file_path, destination=file_path)

    await state.clear()
    await message.answer("Файл получен, запускаю проверку промокодов из файла.")
    await runner.start_with_file(file_path)


@router.message(PromoStates.waiting_file)
async def handle_file_fallback(message: Message) -> None:
    await message.answer("Пожалуйста, отправь файл как документ.")

