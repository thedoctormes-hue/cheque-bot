"""Unit tests for openrouter.py."""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock


class TestParseCheque:

    @pytest.mark.asyncio
    async def test_parse_cheque_returns_correct_dict_structure(self, tmp_path):
        """parse_cheque() returns correct dict structure."""
        test_image = tmp_path / "test_cheque.jpg"
        test_image.write_bytes(b"fake image content")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "date": "2026-05-14",
            "amount": 1250.50,
            "shop": "Магазин Пятёрочка",
            "category": "продукты"
        })

        with patch('services.openrouter._get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            from services.openrouter import parse_cheque
            result = await parse_cheque(str(test_image))

            assert isinstance(result, dict)
            assert 'date' in result
            assert 'amount' in result
            assert 'shop' in result
            assert 'category' in result

    @pytest.mark.asyncio
    async def test_parse_cheque_parses_api_response(self, tmp_path):
        """parse_cheque() correctly parses mocked API response."""
        test_image = tmp_path / "test_cheque.jpg"
        test_image.write_bytes(b"fake image content")

        expected_result = {
            "date": "2026-05-15",
            "amount": 550.00,
            "shop": "Лента",
            "category": "продукты"
        }

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(expected_result)

        with patch('services.openrouter._get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            from services.openrouter import parse_cheque
            result = await parse_cheque(str(test_image))

            assert result == expected_result

    @pytest.mark.asyncio
    async def test_parse_cheque_handles_invalid_json(self, tmp_path):
        """parse_cheque() handles invalid JSON response gracefully."""
        test_image = tmp_path / "test_cheque.jpg"
        test_image.write_bytes(b"fake image content")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "not valid json {{{"

        with patch('services.openrouter._get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            from services.openrouter import parse_cheque
            result = await parse_cheque(str(test_image))

            assert result == {}

    @pytest.mark.asyncio
    async def test_parse_cheque_handles_float_amount(self, tmp_path):
        """parse_cheque() correctly handles float amounts."""
        test_image = tmp_path / "test_cheque.jpg"
        test_image.write_bytes(b"fake image content")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "date": "2026-05-14",
            "amount": 1234.56,
            "shop": "Техносклад",
            "category": "офис"
        })

        with patch('services.openrouter._get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            from services.openrouter import parse_cheque
            result = await parse_cheque(str(test_image))

            assert result['amount'] == 1234.56
            assert isinstance(result['amount'], float)

    @pytest.mark.asyncio
    async def test_parse_cheque_calls_api_with_correct_model(self, tmp_path):
        """parse_cheque() calls API with correct model parameter."""
        test_image = tmp_path / "test_cheque.jpg"
        test_image.write_bytes(b"fake image content")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"date": "2026-05-14", "amount": 100, "shop": "Test", "category": "продукты"}'

        with patch('services.openrouter._get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            from services.openrouter import parse_cheque
            await parse_cheque(str(test_image))

            assert mock_client.chat.completions.create.called
            call_kwargs = mock_client.chat.completions.create.call_args
            assert call_kwargs.kwargs.get('model') == 'google/gemini-2.0-flash-001'
