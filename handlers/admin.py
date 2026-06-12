"""Админские команды: отчёты, экспорт, статистика."""

import csv
import logging
import tempfile
from datetime import datetime, timedelta
from aiogram.types import Message, FSInputFile

from middleware.admin_guard import admin_required
from services.database import get_report_by_period
from services.metrics import get_stats

logger = logging.getLogger(__name__)


async def handle_week(message: Message):
    """Отчёт за последнюю неделю."""
    if not await admin_required(message):
        return

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    try:
        records = get_report_by_period(start_date, end_date)
        if not records:
            await message.answer("За последнюю неделю чеков не было.")
            return

        # Группировка по категориям
        by_category = {}
        total = 0
        for r in records:
            cat = r.get("category", "прочее")
            by_category[cat] = by_category.get(cat, 0) + (r["amount"] or 0)
            total += r["amount"] or 0

        report = f"Отчёт за неделю ({start_date} — {end_date})\n\n"
        for cat, cat_total in sorted(by_category.items()):
            report += f"  {cat}: {cat_total:.2f} руб.\n"
        report += f"\nИтого: {len(records)} чеков на {total:.2f} руб."
        await message.answer(report)

    except Exception as e:
        logger.error(f"Error week report: {e}", exc_info=True)
        await message.answer("Ошибка при формировании отчёта.")


async def handle_month(message: Message):
    """Отчёт за последний месяц."""
    if not await admin_required(message):
        return

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    try:
        records = get_report_by_period(start_date, end_date)
        if not records:
            await message.answer("За последний месяц чеков не было.")
            return

        total = sum(r["amount"] or 0 for r in records)
        report = f"Отчёт за месяц ({start_date} — {end_date})\n\n"
        report += f"Чеков: {len(records)}\n"
        report += f"Итого: {total:.2f} руб."
        await message.answer(report)

    except Exception as e:
        logger.error(f"Error month report: {e}", exc_info=True)
        await message.answer("Ошибка при формировании отчёта.")


async def handle_export(message: Message):
    """Экспорт чеков за месяц в CSV."""
    if not await admin_required(message):
        return

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    try:
        records = get_report_by_period(start_date, end_date)
        if not records:
            await message.answer("Нет данных для экспорта.")
            return

        fd, tmp_path = tempfile.mkstemp(suffix=".csv", prefix="cheques_")
        with open(tmp_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["date", "shop", "amount", "category", "user_id", "created_at"])
            for r in records:
                writer.writerow([
                    r.get("date", ""), r.get("shop", ""), r.get("amount", 0),
                    r.get("category", ""), r.get("user_id", ""), r.get("created_at", "")
                ])
        os.close(fd)

        doc = FSInputFile(tmp_path, filename=f"cheques_{start_date}_{end_date}.csv")
        await message.answer_document(doc, caption=f"Экспорт чеков ({start_date} — {end_date})")
        os.remove(tmp_path)

    except Exception as e:
        logger.error(f"Error export: {e}", exc_info=True)
        await message.answer("Ошибка при экспорте.")


async def handle_stats(message: Message):
    """Внутренняя статистика бота (метрики)."""
    if not await admin_required(message):
        return

    stats = get_stats()
    text = (
        "Статистика бота\n\n"
        f"Распознано чеков: {stats['parsed']}\n"
        f"Сохранено чеков: {stats['saved']}\n"
        f"Ошибок AI: {stats['ai_errors']}\n"
        f"Повторных запросов API: {stats['api_retries']}"
    )
    await message.answer(text)
