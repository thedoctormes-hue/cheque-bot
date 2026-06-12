"""Unit tests for database.py."""
import pytest
import os
import sqlite3
import tempfile
from datetime import datetime


@pytest.fixture
def db():
    """Fresh isolated database for each test."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    old = os.environ.get("DB_PATH")
    os.environ["DB_PATH"] = path
    from services.database import init_db
    init_db()
    yield path
    if old is not None:
        os.environ["DB_PATH"] = old
    else:
        os.environ.pop("DB_PATH", None)
    os.remove(path)


class TestInitDb:
    def test_init_db_creates_table(self, db):
        conn = sqlite3.connect(db)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='cheques'"
        )
        result = cursor.fetchone()
        conn.close()
        assert result is not None
        assert result[0] == "cheques"

    def test_init_db_idempotent(self, db):
        from services.database import init_db
        init_db()
        init_db()
        conn = sqlite3.connect(db)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='cheques'"
        )
        result = cursor.fetchone()
        conn.close()
        assert result is not None

    def test_init_db_creates_indexes(self, db):
        conn = sqlite3.connect(db)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_cheques_date'"
        )
        assert cursor.fetchone() is not None
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_cheques_user'"
        )
        assert cursor.fetchone() is not None
        conn.close()


class TestSaveCheque:
    def test_save_cheque_saves_data_correctly(self, db):
        from services.database import save_cheque, get_all_cheques
        test_data = {
            "date": "2026-05-14", "amount": 150.50, "shop": "Пятёрочка",
            "category": "продукты", "user_id": 12345,
        }
        save_cheque(test_data)
        records = get_all_cheques()
        assert len(records) == 1
        assert records[0]["date"] == "2026-05-14"
        assert records[0]["amount"] == 150.50
        assert records[0]["shop"] == "Пятёрочка"

    def test_save_cheque_with_missing_fields(self, db):
        from services.database import save_cheque, get_all_cheques
        save_cheque({"date": "2026-05-14", "amount": 200.00})
        records = get_all_cheques()
        assert len(records) == 1
        assert records[0]["shop"] is None
        assert records[0]["category"] is None

    def test_save_cheque_multiple_records(self, db):
        from services.database import save_cheque, get_all_cheques
        cheques = [
            {"date": "2026-05-14", "amount": 100, "shop": "A", "category": "продукты", "user_id": 1},
            {"date": "2026-05-14", "amount": 200, "shop": "B", "category": "топливо", "user_id": 2},
            {"date": "2026-05-13", "amount": 300, "shop": "C", "category": "офис", "user_id": 3},
        ]
        for c in cheques:
            save_cheque(c)
        assert len(get_all_cheques()) == 3


class TestGetDailyReport:
    def test_returns_records(self, db):
        from services.database import save_cheque, get_daily_report
        today = datetime.now().strftime("%Y-%m-%d")
        save_cheque({"date": today, "amount": 150.0, "shop": "Test", "category": "продукты", "user_id": 1})
        records = get_daily_report()
        assert len(records) == 1
        assert records[0]["amount"] == 150.0

    def test_filters_by_date(self, db):
        from services.database import save_cheque, get_daily_report
        today = datetime.now().strftime("%Y-%m-%d")
        save_cheque({"date": "2026-05-13", "amount": 500.0, "shop": "Old", "category": "прочее", "user_id": 1})
        save_cheque({"date": today, "amount": 150.0, "shop": "Today", "category": "прочее", "user_id": 1})
        records = get_daily_report()
        assert len(records) == 1
        assert records[0]["shop"] == "Today"

    def test_empty_when_no_records(self, db):
        from services.database import get_daily_report
        assert len(get_daily_report()) == 0


class TestGetReportByPeriod:
    def test_returns_records_in_range(self, db):
        from services.database import save_cheque, get_report_by_period
        save_cheque({"date": "2026-05-12", "amount": 100.0, "shop": "A", "category": "прочее", "user_id": 1})
        save_cheque({"date": "2026-05-14", "amount": 200.0, "shop": "B", "category": "прочее", "user_id": 1})
        save_cheque({"date": "2026-05-20", "amount": 300.0, "shop": "C", "category": "прочее", "user_id": 1})
        records = get_report_by_period("2026-05-10", "2026-05-15")
        assert len(records) == 2

    def test_empty_outside_range(self, db):
        from services.database import save_cheque, get_report_by_period
        save_cheque({"date": "2026-05-14", "amount": 100.0, "shop": "A", "category": "прочее", "user_id": 1})
        records = get_report_by_period("2026-06-01", "2026-06-30")
        assert len(records) == 0

    def test_inclusive_boundaries(self, db):
        from services.database import save_cheque, get_report_by_period
        save_cheque({"date": "2026-05-01", "amount": 50.0, "shop": "Start", "category": "прочее", "user_id": 1})
        save_cheque({"date": "2026-05-31", "amount": 60.0, "shop": "End", "category": "прочее", "user_id": 1})
        records = get_report_by_period("2026-05-01", "2026-05-31")
        assert len(records) == 2

    def test_returns_all_fields(self, db):
        from services.database import save_cheque, get_report_by_period
        save_cheque({"date": "2026-05-14", "amount": 100.0, "shop": "Test", "category": "продукты", "user_id": 42})
        records = get_report_by_period("2026-05-01", "2026-05-31")
        assert len(records) == 1
        r = records[0]
        assert "date" in r
        assert "amount" in r
        assert "shop" in r
        assert "category" in r
        assert "user_id" in r
        assert "created_at" in r

    def test_empty_when_no_data(self, db):
        from services.database import get_report_by_period
        records = get_report_by_period("2026-01-01", "2026-01-31")
        assert len(records) == 0


class TestGetAllCheques:
    def test_returns_all(self, db):
        from services.database import save_cheque, get_all_cheques
        save_cheque({"date": "2026-05-13", "amount": 100, "shop": "A", "category": "прочее", "user_id": 1})
        save_cheque({"date": "2026-05-14", "amount": 200, "shop": "B", "category": "прочее", "user_id": 2})
        assert len(get_all_cheques()) == 2

    def test_empty(self, db):
        from services.database import get_all_cheques
        assert len(get_all_cheques()) == 0


class TestGetConnection:
    def test_returns_connection(self, db):
        from services.database import get_connection
        conn = get_connection()
        assert isinstance(conn, sqlite3.Connection)
        # row_factory установлен
        assert conn.row_factory is not None
        conn.close()

    def test_connection_to_correct_db(self, db):
        from services.database import get_connection
        conn = get_connection()
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        assert "cheques" in tables
        conn.close()
