"""Pytest fixtures for cheque-bot tests."""
import pytest
import tempfile
import os
import sys

sys.path.insert(0, '/root/LabDoctorM/projects/cheque-bot')

from config import ADMIN_ID


@pytest.fixture
def temp_db():
    """Create a temporary database for testing with proper isolation."""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    old_db_path = os.environ.get('DB_PATH')
    os.environ['DB_PATH'] = db_path

    from services.database import init_db
    init_db()

    yield db_path

    if old_db_path is not None:
        os.environ['DB_PATH'] = old_db_path
    elif 'DB_PATH' in os.environ:
        del os.environ['DB_PATH']

    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture(autouse=True)
def set_admin_env():
    """Ensure ADMIN_ID is set for handler tests that need it."""
    old = os.environ.get('ADMIN_ID')
    os.environ['ADMIN_ID'] = '173681771'
    yield
    if old is not None:
        os.environ['ADMIN_ID'] = old


@pytest.fixture
def mock_message():
    """Create a mock Message object with async answer."""
    from unittest.mock import MagicMock, AsyncMock
    message = MagicMock()
    message.from_user = MagicMock()
    message.from_user.id = 12345
    message.answer = AsyncMock()
    return message


@pytest.fixture
def mock_state():
    """Create a mock FSMContext."""
    from unittest.mock import AsyncMock
    state = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()
    state.clear = AsyncMock()
    state.set_state = AsyncMock()
    return state


@pytest.fixture
def admin_message():
    """Create a mock admin Message object (matches ADMIN_ID)."""
    from unittest.mock import MagicMock, AsyncMock
    message = MagicMock()
    message.from_user = MagicMock()
    message.from_user.id = ADMIN_ID
    message.answer = AsyncMock()
    return message


@pytest.fixture
def non_admin_message(mock_message):
    """Create a mock non-admin Message object."""
    mock_message.from_user.id = 12345
    return mock_message
