"""Google Sheets сервис для сохранения чеков (lazy-safe)."""

import logging

import config as cfg

logger = logging.getLogger(__name__)

_enabled: bool | None = None


def _is_enabled() -> bool:
    """Проверяет наличие конфигурации Google Sheets один раз."""
    global _enabled
    if _enabled is None:
        _enabled = bool(cfg.GOOGLE_CREDENTIALS_JSON and cfg.GOOGLE_SHEET_ID)
        if not _enabled:
            logger.info("Google Sheets disabled: no credentials or sheet_id")
    return _enabled


def _get_sheet():
    """Подключается к Google Sheet (импорт gspread при первом вызове)."""
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(
        cfg.GOOGLE_CREDENTIALS_JSON, scopes=scopes
    )
    client = gspread.authorize(creds)
    return client.open_by_key(cfg.GOOGLE_SHEET_ID).sheet1


def save_cheque(data: dict):
    """Сохраняет чек в Google таблицу (если настроено)."""
    if not _is_enabled():
        return

    try:
        sheet = _get_sheet()
        if len(sheet.get_all_values()) == 0:
            sheet.append_row(["date", "amount", "shop", "category", "user_id"])
        sheet.append_row([
            data.get("date"),
            data.get("amount"),
            data.get("shop"),
            data.get("category"),
            data.get("user_id"),
        ])
    except Exception as e:
        logger.warning(f"Google Sheets save failed (non-critical): {e}")
