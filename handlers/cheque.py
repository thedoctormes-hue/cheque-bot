"""Handler для приёма и парсинга чеков с валидацией и inline-коррекцией."""

import logging
import os
from datetime import datetime
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID
from middleware.admin_guard import admin_required
from services.openrouter import parse_cheque
from services.database import init_db, save_cheque, get_daily_report, is_duplicate
from services.validator import validate_cheque, sanitize_cheque
from services import metrics

logger = logging.getLogger(__name__)

VALID_CATEGORIES = ["продукты", "топливо", "офис", "прочее"]


async def handle_start(message: Message):
    init_db()
    await message.answer(
        "Привет! Я бухгалтерский бот.\n\n"
        "Отправь фото чека — я распознаю данные и запишу в отчёт.\n\n"
        "Команды:\n"
        "/report — отчёт за день\n"
        "/week — отчёт за неделю\n"
        "/month — отчёт за месяц\n"
        "/export — экспорт в CSV\n"
        "/stats — статистика\n"
        "/help — помощь"
    )


async def handle_help(message: Message):
    await message.answer(
        "Как использовать:\n\n"
        "1. Сфотографируй чек\n"
        "2. Отправь фото в этот чат\n"
        "3. Я распознаю дату, сумму, магазин\n"
        "4. Подтверди или исправь\n\n"
        "Если я ошибся — исправь кнопками прямо в чате.\n"
        "/cancel — отменить текущее действие"
    )


async def handle_cancel(message: Message, state: FSMContext):
    """Отменяет текущее FSM-состояние."""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нечего отменять.")
    else:
        await state.clear()
        await message.answer("Действие отменено.")


async def handle_photo(message: Message, state: FSMContext):
    """Обрабатывает фото чека с валидацией и inline-коррекцией."""
    bot = message.bot
    # Проверка дубликата
    if is_duplicate(message.message_id):
        await message.answer("Этот чек уже был обработан ранее.")
        return

    await message.answer("Получил фото, парсю чек...")

    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_path = f"/tmp/cheque_{photo.file_id}.jpg"
    await bot.download(file.file_path, destination=file_path)

    try:
        data = await parse_cheque(file_path)

        if not data or not any(data.values()):
            metrics.ai_errors += 1
            await message.answer(
                "Не удалось распознать чек.\n"
                "Попробуй фото получше (чёткое, ровное, хорошее освещение)."
            )
            return

        metrics.cheques_parsed += 1

        validation = validate_cheque(data)
        data = sanitize_cheque(data)

        if not validation.is_valid:
            err_text = "\n".join(f"⚠️ {e}" for e in validation.errors)
            await message.answer(f"Распознано с ошибками:\n{err_text}\n\nПроверь данные:")

        warnings_text = ""
        if validation.warnings:
            warnings_text = "\n".join(f"💡 {w}" for w in validation.warnings)

        cheque_text = (
            f"Распознанный чек:\n\n"
            f"Дата: {data.get('date', '—')}\n"
            f"Сумма: {data.get('amount', '—')} руб.\n"
            f"Магазин: {data.get('shop', '—')}\n"
            f"Категория: {data.get('category', '—')}"
        )
        if warnings_text:
            cheque_text += f"\n\n{warnings_text}"

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Всё верно", callback_data="cheque_confirm"),
                InlineKeyboardButton(text="Исправить", callback_data="cheque_edit"),
            ]
        ])

        await state.update_data(cheque_data=data)
        await message.answer(cheque_text, reply_markup=kb)

    except Exception as e:
        metrics.ai_errors += 1
        logger.error(f"Error parsing cheque: {e}", exc_info=True)
        await message.answer("Ошибка при парсинге чека. Попробуйте снова.")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


async def handle_confirm(callback: CallbackQuery, state: FSMContext):
    """Юзер подтвердил корректность чека."""
    data = await state.get_data()
    cheque_data = data.get("cheque_data", {})
    cheque_data["user_id"] = callback.from_user.id
    cheque_data["message_id"] = callback.message.message_id
    save_cheque(cheque_data)
    metrics.cheques_saved += 1
    await state.clear()

    await callback.message.edit_text(
        f"Чек сохранён!\n\n"
        f"{cheque_data.get('date')} | "
        f"{cheque_data.get('amount')} руб. | "
        f"{cheque_data.get('shop')} | "
        f"{cheque_data.get('category')}"
    )


async def handle_edit_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает меню выбора поля для редактирования."""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Дата", callback_data="edit_date")],
        [InlineKeyboardButton(text="Сумма", callback_data="edit_amount")],
        [InlineKeyboardButton(text="Магазин", callback_data="edit_shop")],
        [InlineKeyboardButton(text="Категория", callback_data="edit_category")],
        [InlineKeyboardButton(text="Сохранить", callback_data="edit_save")],
        [InlineKeyboardButton(text="Отмена", callback_data="edit_cancel")],
    ])
    await callback.message.edit_text("Что исправить?", reply_markup=kb)


async def handle_edit_cancel(callback: CallbackQuery, state: FSMContext):
    """Отменяет редактирование чека."""
    await state.clear()
    await callback.message.edit_text("Редактирование отменено.")


async def handle_edit_field(callback: CallbackQuery, state: FSMContext):
    """Запрашивает новое значение для выбранного поля."""
    field = callback.data.replace("edit_", "")
    await state.update_data(editing_field=field)

    prompts = {
        "date": "Введи дату в формате ДД.ММ.ГГГГ:",
        "amount": "Введи сумму (число):",
        "shop": "Введи название магазина:",
        "category": f"Выбери категорию: {', '.join(VALID_CATEGORIES)}",
    }
    await callback.message.edit_text(prompts.get(field, f"Введи новое значение для {field}:"))


async def handle_edit_input(message: Message, state: FSMContext):
    """Принимает новое значение поля и обновляет чек."""
    data = await state.get_data()
    field = data.get("editing_field")
    cheque_data = data.get("cheque_data", {})
    value = message.text.strip()

    if field == "date":
        try:
            dt = datetime.strptime(value, "%d.%m.%Y")
            cheque_data["date"] = dt.strftime("%Y-%m-%d")
        except ValueError:
            await message.answer("Неправильный формат. Используй ДД.ММ.ГГГГ (например: 31.05.2026)")
            return
    elif field == "amount":
        try:
            cheque_data["amount"] = float(value.replace(",", "."))
        except ValueError:
            await message.answer("Неправильный формат суммы. Введи число.")
            return
    elif field == "category":
        if value.lower() not in VALID_CATEGORIES:
            await message.answer(f"Категория должна быть одна из: {', '.join(VALID_CATEGORIES)}")
            return
        cheque_data["category"] = value.lower()
    else:
        cheque_data[field] = value[:100]

    await state.update_data(cheque_data=cheque_data)

    cheque_text = (
        f"Обновлённый чек:\n\n"
        f"Дата: {cheque_data.get('date', '—')}\n"
        f"Сумма: {cheque_data.get('amount', '—')} руб.\n"
        f"Магазин: {cheque_data.get('shop', '—')}\n"
        f"Категория: {cheque_data.get('category', '—')}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Сохранить", callback_data="edit_save"),
            InlineKeyboardButton(text="Ещё исправить", callback_data="cheque_edit"),
        ]
    ])
    await message.answer(cheque_text, reply_markup=kb)


async def handle_edit_save(callback: CallbackQuery, state: FSMContext):
    """Сохраняет отредактированный чек в БД."""
    data = await state.get_data()
    cheque_data = data.get("cheque_data", {})
    cheque_data["user_id"] = callback.from_user.id
    cheque_data["message_id"] = callback.message.message_id
    save_cheque(cheque_data)
    metrics.cheques_saved += 1
    await state.clear()

    await callback.message.edit_text(
        f"Чек сохранён!\n\n"
        f"{cheque_data.get('date')} | "
        f"{cheque_data.get('amount')} руб. | "
        f"{cheque_data.get('shop')} | "
        f"{cheque_data.get('category')}"
    )


async def handle_report(message: Message):
    """Отправляет отчёт за сегодня бухгалтеру."""
    if not await admin_required(message):
        return

    try:
        records = get_daily_report()

        if not records:
            await message.answer("Сегодня чеков не было.")
            return

        total = sum(r["amount"] or 0 for r in records)
        report = f"Отчёт за {datetime.now().strftime('%Y-%m-%d')}\n\n"
        for r in records:
            report += f"• {r['shop']}: {r['amount']} руб.\n"
        report += f"\nИтого: {total:.2f} руб."

        await message.answer(report)

    except Exception as e:
        logger.error(f"Error generating report: {e}", exc_info=True)
        await message.answer("Ошибка при формировании отчёта.")
