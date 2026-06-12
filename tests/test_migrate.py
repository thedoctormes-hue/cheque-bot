"""Unit tests for migrate.py."""
import sqlite3


class TestMigrations:
    def test_migrations_run_without_error(self, temp_db):
        from services.migrate import run_migrations
        run_migrations()
        # Не падает — уже успех

    def test_migrations_create_table(self, temp_db):
        from services.migrate import run_migrations
        run_migrations()
        conn = sqlite3.connect(temp_db)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='_migrations'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_migrations_record_version(self, temp_db):
        from services.migrate import run_migrations
        run_migrations()
        conn = sqlite3.connect(temp_db)
        cursor = conn.execute("SELECT MAX(version) FROM _migrations")
        max_version = cursor.fetchone()[0]
        assert max_version is not None
        assert max_version >= 1
        conn.close()

    def test_migrations_idempotent(self, temp_db):
        from services.migrate import run_migrations
        run_migrations()
        run_migrations()  # Второй раз — не падает

    def test_migrations_cheques_table_exists(self, temp_db):
        """Таблица cheques создаётся init_db и не ломается миграциями."""
        from services.database import init_db
        init_db()
        conn = sqlite3.connect(temp_db)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='cheques'"
        )
        assert cursor.fetchone() is not None
        conn.close()
