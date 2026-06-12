"""Unit tests for admin.py handlers."""
import pytest
from unittest.mock import patch


class TestAdminAccess:
    """Проверка доступа к админским командам."""

    @pytest.mark.asyncio
    async def test_week_allowed_for_admin(self, admin_message, temp_db):
        from handlers.admin import handle_week
        with patch("handlers.admin.get_report_by_period", return_value=[]):
            await handle_week(admin_message)
            assert admin_message.answer.called

    @pytest.mark.asyncio
    async def test_week_blocks_non_admin(self, non_admin_message, temp_db):
        from handlers.admin import handle_week
        await handle_week(non_admin_message)
        text = non_admin_message.answer.call_args[0][0]
        assert "нет доступа" in text.lower() or "нет доступа" in text

    @pytest.mark.asyncio
    async def test_month_allowed_for_admin(self, admin_message, temp_db):
        from handlers.admin import handle_month
        with patch("handlers.admin.get_report_by_period", return_value=[]):
            await handle_month(admin_message)
            assert admin_message.answer.called

    @pytest.mark.asyncio
    async def test_month_blocks_non_admin(self, non_admin_message, temp_db):
        from handlers.admin import handle_month
        await handle_month(non_admin_message)
        text = non_admin_message.answer.call_args[0][0]
        assert "нет доступа" in text.lower()

    @pytest.mark.asyncio
    async def test_export_allowed_for_admin(self, admin_message, temp_db):
        from handlers.admin import handle_export
        with patch("handlers.admin.get_report_by_period", return_value=[]):
            await handle_export(admin_message)
            assert admin_message.answer.called

    @pytest.mark.asyncio
    async def test_export_blocks_non_admin(self, non_admin_message, temp_db):
        from handlers.admin import handle_export
        await handle_export(non_admin_message)
        text = non_admin_message.answer.call_args[0][0]
        assert "нет доступа" in text.lower()

    @pytest.mark.asyncio
    async def test_stats_allowed_for_admin(self, admin_message, temp_db):
        from handlers.admin import handle_stats
        await handle_stats(admin_message)
        assert admin_message.answer.called

    @pytest.mark.asyncio
    async def test_stats_blocks_non_admin(self, non_admin_message, temp_db):
        from handlers.admin import handle_stats
        await handle_stats(non_admin_message)
        text = non_admin_message.answer.call_args[0][0]
        assert "нет доступа" in text.lower()


class TestWeekReport:
    @pytest.mark.asyncio
    async def test_week_empty(self, admin_message, temp_db):
        from handlers.admin import handle_week
        with patch("handlers.admin.get_report_by_period", return_value=[]):
            await handle_week(admin_message)
            text = admin_message.answer.call_args[0][0]
            assert "не было" in text.lower()

    @pytest.mark.asyncio
    async def test_week_with_data(self, admin_message, temp_db):
        from handlers.admin import handle_week
        mock_records = [
            {"amount": 150.0, "category": "продукты"},
            {"amount": 250.0, "category": "топливо"},
            {"amount": 100.0, "category": "продукты"},
        ]
        with patch("handlers.admin.get_report_by_period", return_value=mock_records):
            await handle_week(admin_message)
            text = admin_message.answer.call_args[0][0]
            assert "продукты" in text
            assert "топливо" in text
            assert "500" in text or "300" in text
            assert "3 чеков" in text


class TestMonthReport:
    @pytest.mark.asyncio
    async def test_month_empty(self, admin_message, temp_db):
        from handlers.admin import handle_month
        with patch("handlers.admin.get_report_by_period", return_value=[]):
            await handle_month(admin_message)
            text = admin_message.answer.call_args[0][0]
            assert "не было" in text.lower()

    @pytest.mark.asyncio
    async def test_month_with_data(self, admin_message, temp_db):
        from handlers.admin import handle_month
        mock_records = [
            {"amount": 300.0, "category": "офис"},
            {"amount": 500.0, "category": "продукты"},
        ]
        with patch("handlers.admin.get_report_by_period", return_value=mock_records):
            await handle_month(admin_message)
            text = admin_message.answer.call_args[0][0]
            assert "800" in text
            assert "2" in text


class TestStats:
    @pytest.mark.asyncio
    async def test_stats_format(self, admin_message, temp_db):
        from handlers.admin import handle_stats
        await handle_stats(admin_message)
        text = admin_message.answer.call_args[0][0]
        assert "Распознано" in text or "parsed" in text.lower()
        assert "Сохранено" in text or "saved" in text.lower()
        assert "Ошибок" in text or "errors" in text.lower()
