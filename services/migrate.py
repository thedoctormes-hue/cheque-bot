"""Простые миграции SQLite."""

import logging
from services.database import get_connection

logger = logging.getLogger(__name__)

MIGRATIONS = [
    # v1: индекс по дате (таблица уже создана init_db())
    "CREATE INDEX IF NOT EXISTS idx_cheques_date ON cheques(date)",
    # v2: индекс по user_id
    "CREATE INDEX IF NOT EXISTS idx_cheques_user ON cheques(user_id)",
]


def run_migrations():
    """Применяет миграции, которые ещё не были применены."""
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT DEFAULT (datetime('now'))
            )
        """)
        current = conn.execute(
            "SELECT MAX(version) FROM _migrations"
        ).fetchone()[0] or 0

        for i, sql in enumerate(MIGRATIONS, start=1):
            if i > current:
                logger.info(f"Applying migration v{i}")
                try:
                    conn.execute(sql)
                    conn.execute(
                        "INSERT INTO _migrations (version) VALUES (?)", (i,)
                    )
                    conn.commit()
                except Exception as e:
                    # Колонка уже существует — не ошибка
                    logger.warning(f"Migration v{i} skipped: {e}")
                    conn.rollback()
                    conn.execute(
                        "INSERT INTO _migrations (version) VALUES (?)", (i,)
                    )
                    conn.commit()

        logger.info(f"Database at migration v{len(MIGRATIONS)}")
    finally:
        conn.close()
