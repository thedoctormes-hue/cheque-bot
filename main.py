#!/usr/bin/env python3
"""Telegram бот для автоматизации бухгалтерии с AI парсингом чеков."""

import asyncio
import logging
import signal
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher, BaseMiddleware, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

import config as cfg


def _setup_logging() -> logging.Logger:
    """Настраивает логирование с ротацией."""
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotating file: 5 файлов по 10MB
    file_handler = RotatingFileHandler(
        cfg.LOG_PATH, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    console_handler.setLevel(logging.INFO)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    return logging.getLogger(__name__)


# ── Middleware ───────────────────────────────────────────────────────────────

class ErrorLoggingMiddleware(BaseMiddleware):
    """Логирует неожиданные ошибки в хендлерах, не роняя бота."""

    async def __call__(self, handler, event, data):
        try:
            return await handler(event, data)
        except Exception as exc:
            logging.getLogger("error").error(
                f"Unhandled error in handler: {exc}", exc_info=True
            )
            raise


# ── Application ─────────────────────────────────────────────────────────────

async def main():
    logger = _setup_logging()
    logger.info("Starting cheque-bot...")

    bot = Bot(token=cfg.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.message.middleware(ErrorLoggingMiddleware())

    # ── Handlers ────────────────────────────────────────────────────────────

    from handlers.cheque import (
        handle_start, handle_help, handle_photo, handle_report,
        handle_confirm, handle_edit_menu, handle_edit_field,
        handle_edit_input, handle_edit_save, handle_edit_cancel,
        handle_cancel,
    )
    from handlers.admin import (
        handle_week, handle_month, handle_export, handle_stats,
    )

    dp.message.register(handle_start, Command("start"))
    dp.message.register(handle_help, Command("help"))
    dp.message.register(handle_report, Command("report"))
    dp.message.register(handle_week, Command("week"))
    dp.message.register(handle_month, Command("month"))
    dp.message.register(handle_export, Command("export"))
    dp.message.register(handle_stats, Command("stats"))
    dp.message.register(handle_cancel, Command("cancel"))
    dp.message.register(handle_photo, F.photo)

    # Сообщения в состоянии FSM (текстовые, не команды)
    dp.message.register(
        handle_edit_input,
        F.text & ~F.text.startswith("/"),
    )

    # Callback handlers
    dp.callback_query.register(handle_confirm, lambda c: c.data == "cheque_confirm")
    dp.callback_query.register(handle_edit_menu, lambda c: c.data == "cheque_edit")
    dp.callback_query.register(handle_edit_save, lambda c: c.data == "edit_save")
    dp.callback_query.register(handle_edit_cancel, lambda c: c.data == "edit_cancel")
    dp.callback_query.register(handle_edit_field, lambda c: c.data and c.data.startswith("edit_"))

    # ── Background tasks ────────────────────────────────────────────────────

    from services.queue import process_queue
    from services.openrouter import parse_cheque

    async def queue_worker():
        while True:
            try:
                await process_queue(bot, parse_cheque)
            except Exception as e:
                logger.error(f"Queue worker error: {e}")
            await asyncio.sleep(60)

    queue_task = asyncio.create_task(queue_worker())

    # ── Graceful shutdown ───────────────────────────────────────────────────

    shutdown_event = asyncio.Event()

    def _shutdown(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        shutdown_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _shutdown, sig, None)
        except NotImplementedError:
            signal.signal(sig, _shutdown)

    # ── Start polling ───────────────────────────────────────────────────────

    polling_task = asyncio.create_task(dp.start_polling(bot))

    await shutdown_event.wait()
    logger.info("Stopping polling...")
    await dp.stop_polling()
    queue_task.cancel()
    try:
        await queue_task
    except asyncio.CancelledError:
        pass
    logger.info("Bot stopped gracefully.")


if __name__ == "__main__":
    asyncio.run(main())
