"""Tests for new features: delete, update, cancel, duplicate check."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestDeleteCheque:
    def test_delete_existing_cheque(self, temp_db):
        from services.database import save_cheque, delete_cheque, get_all_cheques
        save_cheque({"date": "2026-05-14", "amount": 100, "shop": "Test", "category": "прочее", "user_id": 1})
        cheque = get_all_cheques()[0]
        assert delete_cheque(cheque["id"], user_id=1) is True
        assert len(get_all_cheques()) == 0

    def test_delete_wrong_user(self, temp_db):
        from services.database import save_cheque, delete_cheque, get_all_cheques
        save_cheque({"date": "2026-05-14", "amount": 100, "shop": "Test", "category": "прочее", "user_id": 1})
        cheque = get_all_cheques()[0]
        assert delete_cheque(cheque["id"], user_id=999) is False
        assert len(get_all_cheques()) == 1

    def test_delete_nonexistent(self, temp_db):
        from services.database import delete_cheque
        assert delete_cheque(9999, user_id=1) is False


class TestUpdateCheque:
    def test_update_fields(self, temp_db):
        from services.database import save_cheque, update_cheque, get_cheque_by_id, get_all_cheques
        save_cheque({"date": "2026-05-14", "amount": 100, "shop": "Old", "category": "прочее", "user_id": 1})
        cid = get_all_cheques()[0]["id"]
        assert update_cheque(cid, user_id=1, data={"shop": "New Shop", "amount": 200}) is True
        updated = get_cheque_by_id(cid)
        assert updated["shop"] == "New Shop"
        assert updated["amount"] == 200

    def test_update_wrong_user(self, temp_db):
        from services.database import save_cheque, update_cheque, get_all_cheques
        save_cheque({"date": "2026-05-14", "amount": 100, "shop": "Test", "category": "прочее", "user_id": 1})
        cid = get_all_cheques()[0]["id"]
        assert update_cheque(cid, user_id=999, data={"shop": "Hacked"}) is False

    def test_update_ignores_unknown_fields(self, temp_db):
        from services.database import save_cheque, update_cheque, get_all_cheques
        save_cheque({"date": "2026-05-14", "amount": 100, "shop": "Test", "category": "прочее", "user_id": 1})
        cid = get_all_cheques()[0]["id"]
        assert update_cheque(cid, user_id=1, data={"hacked": True, "shop": "OK"}) is True


class TestGetChequeById:
    def test_returns_cheque(self, temp_db):
        from services.database import save_cheque, get_cheque_by_id, get_all_cheques
        save_cheque({"date": "2026-05-14", "amount": 100, "shop": "Test", "category": "прочее", "user_id": 1})
        cid = get_all_cheques()[0]["id"]
        result = get_cheque_by_id(cid)
        assert result is not None
        assert result["shop"] == "Test"

    def test_returns_none_for_missing(self, temp_db):
        from services.database import get_cheque_by_id
        assert get_cheque_by_id(9999) is None


class TestDuplicateCheck:
    def test_duplicate_detected(self, temp_db):
        from services.database import save_cheque, is_duplicate
        save_cheque({"date": "2026-05-14", "amount": 100, "shop": "Test", "category": "прочее", "user_id": 1, "message_id": 12345})
        assert is_duplicate(12345) is True

    def test_no_duplicate(self, temp_db):
        from services.database import is_duplicate
        assert is_duplicate(99999) is False

    def test_zero_message_id_not_checked(self, temp_db):
        from services.database import is_duplicate
        assert is_duplicate(0) is False


class TestCancelHandler:
    @pytest.mark.asyncio
    async def test_cancel_clears_state(self, mock_message, mock_state):
        from handlers.cheque import handle_cancel
        mock_state.get_state = AsyncMock(return_value="some_state")
        await handle_cancel(mock_message, mock_state)
        mock_state.clear.assert_called_once()
        mock_message.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_noop_when_no_state(self, mock_message, mock_state):
        from handlers.cheque import handle_cancel
        mock_state.get_state = AsyncMock(return_value=None)
        await handle_cancel(mock_message, mock_state)
        mock_state.clear.assert_not_called()
        assert "Нечего отменять" in mock_message.answer.call_args[0][0]


class TestEditCancel:
    @pytest.mark.asyncio
    async def test_edit_cancel_clears_state(self):
        from handlers.cheque import handle_edit_cancel
        callback = AsyncMock()
        callback.message.message_id = 1
        state = AsyncMock()
        await handle_edit_cancel(callback, state)
        state.clear.assert_called_once()
        callback.message.edit_text.assert_called_once()
