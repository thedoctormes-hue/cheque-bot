"""Unit tests for queue.py."""
import pytest
import os
import json
from unittest.mock import AsyncMock, patch


@pytest.fixture
def queue_env(tmp_path, monkeypatch):
    """Настраивает временную директорию для очереди."""
    monkeypatch.setattr("services.queue.QUEUE_DIR", str(tmp_path / "queue"))
    return tmp_path


class TestEnqueue:
    @pytest.mark.asyncio
    async def test_enqueue_creates_meta_file(self, queue_env):
        from services.queue import enqueue
        photo_path = str(queue_env / "test.jpg")
        with open(photo_path, "w") as f:
            f.write("fake")
        await enqueue(photo_path, user_id=123, message_id=456)

        meta_files = list((queue_env / "queue").glob("*.json"))
        assert len(meta_files) == 1

    @pytest.mark.asyncio
    async def test_enqueue_meta_content(self, queue_env):
        from services.queue import enqueue
        photo_path = str(queue_env / "test.jpg")
        with open(photo_path, "w") as f:
            f.write("fake")
        await enqueue(photo_path, user_id=123, message_id=789)

        meta_file = list((queue_env / "queue").glob("*.json"))[0]
        with open(meta_file) as f:
            meta = json.load(f)
        assert meta["user_id"] == 123
        assert meta["message_id"] == 789
        assert meta["retries"] == 0


class TestProcessQueue:
    @pytest.mark.asyncio
    async def test_process_empty_queue(self, queue_env):
        from services.queue import process_queue
        bot = AsyncMock()
        parse_func = AsyncMock()
        await process_queue(bot, parse_func)
        parse_func.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_queue_removes_completed_task(self, queue_env):
        from services.queue import enqueue, process_queue
        photo_path = str(queue_env / "test.jpg")
        with open(photo_path, "wb") as f:
            f.write(b"fake")
        await enqueue(photo_path, user_id=123, message_id=1)

        bot = AsyncMock()
        parse_func = AsyncMock(return_value={"date": "2026-01-01", "amount": 100})

        with patch("services.queue.os.path.exists", return_value=True):
            await process_queue(bot, parse_func)

        meta_files = list((queue_env / "queue").glob("*.json"))
        assert len(meta_files) == 0

    @pytest.mark.asyncio
    async def test_process_queue_retries_on_empty_result(self, queue_env):
        from services.queue import enqueue, process_queue
        photo_path = str(queue_env / "test.jpg")
        with open(photo_path, "wb") as f:
            f.write(b"fake")
        await enqueue(photo_path, user_id=123, message_id=2)

        bot = AsyncMock()
        parse_func = AsyncMock(return_value={})

        await process_queue(bot, parse_func)

        # Должен остаться retry-файл
        meta_files = list((queue_env / "queue").glob("*.json"))
        assert len(meta_files) == 1
        with open(meta_files[0]) as f:
            meta = json.load(f)
        assert meta["retries"] == 1

    @pytest.mark.asyncio
    async def test_process_queue_drops_after_max_retries(self, queue_env):
        from services.queue import process_queue, QUEUE_DIR

        # Создаём задачу с retries=3 (max exceeded)
        os.makedirs(QUEUE_DIR, exist_ok=True)
        meta = {
            "photo_path": "/tmp/nonexistent.jpg",
            "user_id": 123,
            "message_id": 3,
            "enqueued_at": "2026-01-01T00:00:00",
            "retries": 3,
        }
        with open(os.path.join(QUEUE_DIR, "task_3.json"), "w") as f:
            json.dump(meta, f)

        bot = AsyncMock()
        parse_func = AsyncMock()

        await process_queue(bot, parse_func)

        meta_files = list((queue_env / "queue").glob("*.json"))
        assert len(meta_files) == 0
