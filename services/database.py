"""SQLite хранилище для чеков."""

import sqlite3
import os
from datetime import datetime

import config as cfg

DEFAULT_DB = cfg.DB_PATH


def _db_path() -> str:
    """Читает DB_PATH из env при каждом вызове — корректно работает с тестами."""
    return os.getenv("DB_PATH", DEFAULT_DB)


def get_connection() -> sqlite3.Connection:
    """Возвращает соединение с БД (для миграций и сложных запросов)."""
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Создаёт таблицу и индексы если не существуют."""
    with sqlite3.connect(_db_path()) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cheques (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                amount REAL,
                shop TEXT,
                category TEXT DEFAULT 'прочее',
                user_id INTEGER,
                message_id INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cheques_date ON cheques(date)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cheques_user ON cheques(user_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cheques_message ON cheques(message_id)"
        )
        conn.commit()


def save_cheque(data: dict):
    """Сохраняет чек в БД."""
    with sqlite3.connect(_db_path()) as conn:
        conn.execute(
            "INSERT INTO cheques (date, amount, shop, category, user_id, message_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                data.get("date"),
                data.get("amount"),
                data.get("shop"),
                data.get("category"),
                data.get("user_id"),
                data.get("message_id", 0),
            ),
        )
        conn.commit()


def is_duplicate(message_id: int) -> bool:
    """Проверяет, был ли чек с таким message_id уже сохранён."""
    try:
        mid = int(message_id)
    except (TypeError, ValueError):
        return False
    if not mid:
        return False
    with sqlite3.connect(_db_path()) as conn:
        cursor = conn.execute(
            "SELECT 1 FROM cheques WHERE message_id = ?", (mid,)
        )
        return cursor.fetchone() is not None


def get_daily_report() -> list[dict]:
    """Возвращает чеки за сегодня."""
    today = datetime.now().strftime("%Y-%m-%d")
    with sqlite3.connect(_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT date, amount, shop, category FROM cheques "
            "WHERE date = ? ORDER BY created_at DESC",
            (today,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_report_by_period(start_date: str, end_date: str) -> list[dict]:
    """Возвращает чеки за период [start_date, end_date]."""
    with sqlite3.connect(_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT date, amount, shop, category, user_id, created_at "
            "FROM cheques WHERE date BETWEEN ? AND ? "
            "ORDER BY created_at DESC",
            (start_date, end_date),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_all_cheques() -> list[dict]:
    """Все чеки для экспорта."""
    with sqlite3.connect(_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM cheques ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]


def get_cheque_by_id(cheque_id: int) -> dict | None:
    """Возвращает чек по ID или None."""
    with sqlite3.connect(_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM cheques WHERE id = ?", (cheque_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def delete_cheque(cheque_id: int, user_id: int) -> bool:
    """Удаляет чек по ID, если он принадлежит user_id. Возвращает True если удалён."""
    with sqlite3.connect(_db_path()) as conn:
        cursor = conn.execute(
            "DELETE FROM cheques WHERE id = ? AND user_id = ?",
            (cheque_id, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def update_cheque(cheque_id: int, user_id: int, data: dict) -> bool:
    """Обновляет поля чека по ID, если он принадлежит user_id. Возвращает True если обновлён."""
    allowed_fields = {"date", "amount", "shop", "category"}
    updates = {k: v for k, v in data.items() if k in allowed_fields}
    if not updates:
        return False

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [cheque_id, user_id]

    with sqlite3.connect(_db_path()) as conn:
        cursor = conn.execute(
            f"UPDATE cheques SET {set_clause} WHERE id = ? AND user_id = ?",
            values,
        )
        conn.commit()
        return cursor.rowcount > 0
