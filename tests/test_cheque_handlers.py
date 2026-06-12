"""Unit tests for cheque.py handlers."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from config import ADMIN_ID


@pytest.fixture(autouse=True)
def _mock_openrouter():
    """Mock parse_cheque for all handler tests."""
    with patch('handlers.cheque.parse_cheque', new_callable=AsyncMock) as mock:
        mock.return_value = {
            'date': '2026-05-14',
            'amount': 100.00,
            'shop': 'Test Shop',
            'category': 'продукты'
        }
        yield mock


class TestHandleStart:
    """Tests for handle_start function."""

    @pytest.mark.asyncio
    async def test_handle_start_sends_correct_message(self, mock_message, temp_db):
        """handle_start() sends correct welcome message."""
        from handlers.cheque import handle_start

        await handle_start(mock_message)

        assert mock_message.answer.called
        call_args = mock_message.answer.call_args
        message_text = call_args[0][0]

        assert "Привет" in message_text
        assert "/report" in message_text
        assert "/help" in message_text

    @pytest.mark.asyncio
    async def test_handle_start_initializes_database(self, mock_message, temp_db):
        """handle_start() initializes database on start."""
        from handlers.cheque import handle_start

        with patch('handlers.cheque.init_db') as mock_init_db:
            await handle_start(mock_message)
            mock_init_db.assert_called_once()


class TestHandleHelp:
    """Tests for handle_help function."""

    @pytest.mark.asyncio
    async def test_handle_help_sends_help_text(self, mock_message, temp_db):
        """handle_help() sends help text."""
        from handlers.cheque import handle_help

        await handle_help(mock_message)

        assert mock_message.answer.called
        call_args = mock_message.answer.call_args
        message_text = call_args[0][0]

        assert "Как использовать" in message_text
        assert "Сфотографируй чек" in message_text


class TestHandleReport:
    """Tests for handle_report function."""

    @pytest.mark.asyncio
    async def test_handle_report_works_for_admin(self, admin_message, temp_db):
        """handle_report() works for admin."""
        from handlers.cheque import handle_report

        with patch('handlers.cheque.get_daily_report') as mock_get_report:
            mock_get_report.return_value = []

            await handle_report(admin_message)

            mock_get_report.assert_called_once()
            assert admin_message.answer.called

    @pytest.mark.asyncio
    async def test_handle_report_blocks_non_admin(self, non_admin_message, temp_db):
        """handle_report() blocks non-admin users."""
        from handlers.cheque import handle_report

        await handle_report(non_admin_message)

        assert non_admin_message.answer.called
        call_args = non_admin_message.answer.call_args
        message_text = call_args[0][0]

        assert "нет доступа" in message_text or "❌" in message_text

    @pytest.mark.asyncio
    async def test_handle_report_empty_when_no_records(self, admin_message, temp_db):
        """handle_report() returns message when no records exist."""
        from handlers.cheque import handle_report

        with patch('handlers.cheque.get_daily_report') as mock_get_report:
            mock_get_report.return_value = []

            await handle_report(admin_message)

            call_args = admin_message.answer.call_args
            message_text = call_args[0][0]

            assert "не было" in message_text or "нет" in message_text.lower()

    @pytest.mark.asyncio
    async def test_handle_report_formats_records_correctly(self, admin_message, temp_db):
        """handle_report() formats multiple records correctly."""
        from handlers.cheque import handle_report

        mock_records = [
            {'date': '2026-05-14', 'amount': 150.00, 'shop': 'Shop A', 'category': 'продукты'},
            {'date': '2026-05-14', 'amount': 250.00, 'shop': 'Shop B', 'category': 'топливо'},
        ]

        with patch('handlers.cheque.get_daily_report', return_value=mock_records):
            await handle_report(admin_message)

            call_args = admin_message.answer.call_args
            message_text = call_args[0][0]

            assert "Shop A" in message_text
            assert "Shop B" in message_text
            assert "400" in message_text


class TestHandlePhoto:
    """Tests for handle_photo function."""

    @pytest.mark.asyncio
    async def test_handle_photo_processes_image(self, mock_message, mock_state, temp_db):
        """handle_photo() получает фото и показывает результат с inline-кнопками."""
        from handlers.cheque import handle_photo

        mock_message.photo = [MagicMock(), MagicMock(file_id='test_file_id')]
        mock_bot = AsyncMock()
        mock_message.bot = mock_bot
        mock_file = MagicMock()
        mock_file.file_path = 'photos/test.jpg'
        mock_bot.get_file = AsyncMock(return_value=mock_file)
        mock_bot.download = AsyncMock()
        mock_message.answer = AsyncMock()

        await handle_photo(mock_message, mock_state)

        mock_bot.get_file.assert_called_once()
        mock_bot.download.assert_called_once()
        assert mock_message.answer.call_count >= 2

    @pytest.mark.asyncio
    async def test_handle_photo_ai_returns_empty(self, mock_message, mock_state, temp_db):
        """handle_photo() обрабатывает пустой ответ AI."""
        from handlers.cheque import handle_photo

        with patch('handlers.cheque.parse_cheque', new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = {}

            mock_message.photo = [MagicMock(), MagicMock(file_id='test1')]
            mock_bot = AsyncMock()
            mock_message.bot = mock_bot
            mock_bot.get_file = AsyncMock(return_value=MagicMock(file_path='x.jpg'))
            mock_bot.download = AsyncMock()
            mock_message.answer = AsyncMock()

            await handle_photo(mock_message, mock_state)

            answer_text = mock_message.answer.call_args[0][0]
            assert 'не удалось' in answer_text.lower() or 'ошибка' in answer_text.lower()


class TestValidator:
    """Tests for validate_cheque and sanitize_cheque."""

    def test_validate_valid_cheque(self):
        from services.validator import validate_cheque
        data = {'date': '2026-05-14', 'amount': 150.0, 'shop': 'Пятёрочка', 'category': 'продукты'}
        result = validate_cheque(data)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_suspicious_year(self):
        from services.validator import validate_cheque
        data = {'date': '1999-05-14', 'amount': 150.0, 'shop': 'Тест', 'category': 'прочее'}
        result = validate_cheque(data)
        assert len(result.warnings) > 0

    def test_validate_zero_amount(self):
        from services.validator import validate_cheque
        data = {'date': '2026-05-14', 'amount': 0, 'shop': 'Тест', 'category': 'прочее'}
        result = validate_cheque(data)
        assert not result.is_valid

    def test_validate_negative_amount(self):
        from services.validator import validate_cheque
        data = {'date': '2026-05-14', 'amount': -50, 'shop': 'Тест', 'category': 'прочее'}
        result = validate_cheque(data)
        assert not result.is_valid

    def test_validate_empty_shop(self):
        from services.validator import validate_cheque
        data = {'date': '2026-05-14', 'amount': 100, 'shop': '', 'category': 'прочее'}
        result = validate_cheque(data)
        assert not result.is_valid

    def test_validate_future_date(self):
        from services.validator import validate_cheque
        data = {'date': '2099-01-01', 'amount': 100, 'shop': 'Тест', 'category': 'прочее'}
        result = validate_cheque(data)
        assert not result.is_valid

    def test_validate_missing_fields(self):
        from services.validator import validate_cheque
        result = validate_cheque({})
        assert not result.is_valid
        assert len(result.errors) >= 3

    def test_sanitize_ru_date(self):
        from services.validator import sanitize_cheque
        data = {'date': '14.05.2026', 'amount': '150,50', 'shop': '  пятёрочка  ', 'category': 'Продукты'}
        result = sanitize_cheque(data)
        assert result['date'] == '2026-05-14'
        assert result['amount'] == 150.5
        assert 'Пятёрочка' in result['shop']
        assert result['category'] == 'продукты'

    def test_sanitize_empty_category(self):
        from services.validator import sanitize_cheque
        result = sanitize_cheque({'category': 'unknown'})
        assert result['category'] == 'прочее'

    def test_sanitize_huge_amount_warning(self):
        from services.validator import validate_cheque
        data = {'date': '2026-05-14', 'amount': 999999, 'shop': 'Тест', 'category': 'прочее'}
        result = validate_cheque(data)
        assert len(result.warnings) > 0
