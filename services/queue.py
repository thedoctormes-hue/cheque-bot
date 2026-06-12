"""Простая in-memory очередь для повторной обработки чеков при ошибках AI."""

import os
import json
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

QUEUE_DIR = "/tmp/cheque_queue"


async def enqueue(photo_path: str, user_id: int, message_id: int):
    """Сохраняет фото для повторной обработки."""
    os.makedirs(QUEUE_DIR, exist_ok=True)
    meta = {
        "photo_path": photo_path,
        "user_id": user_id,
        "message_id": message_id,
        "enqueued_at": datetime.now().isoformat(),
        "retries": 0,
    }
    meta_path = os.path.join(QUEUE_DIR, f"task_{message_id}.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f)
    logger.info(f"Enqueued task for message {message_id}")


async def process_queue(bot, parse_func):
    """Обрабатывает очередь отложенных задач. Вызывать из фонового таска."""
    if not os.path.exists(QUEUE_DIR):
        return

    files = [f for f in os.listdir(QUEUE_DIR) if f.endswith(".json")]
    if not files:
        return

    for filename in files:
        if not filename.endswith(".json"):
            continue

        meta_path = os.path.join(QUEUE_DIR, filename)
        try:
            with open(meta_path) as f:
                meta = json.load(f)
        except (json.JSONDecodeError, IOError):
            os.remove(meta_path)
            continue

        retries = meta.get("retries", 0)
        if retries >= 3:
            logger.warning(f"Task {filename} exceeded max retries, removing")
            os.remove(meta_path)
            continue

        photo_path = meta.get("photo_path")
        user_id = meta.get("user_id")

        if not photo_path or not os.path.exists(photo_path):
            os.remove(meta_path)
            continue

        try:
            data = await parse_func(photo_path)
            if data and any(data.values()):
                logger.info(f"Queue task {filename} processed successfully")
                os.remove(meta_path)
                if os.path.exists(photo_path):
                    os.remove(photo_path)
            else:
                raise ValueError("Empty AI response")
        except Exception as e:
            meta["retries"] = retries + 1
            with open(meta_path, "w") as f:
                json.dump(meta, f)
            logger.warning(f"Queue task {filename} failed (retry {retries + 1}): {e}")
            await asyncio.sleep(5)
