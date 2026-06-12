"""Единая точка конфигурации cheque-bot."""

import os
from dotenv import load_dotenv

_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(_env_path)

BOT_TOKEN: str = os.environ["BOT_TOKEN"]
OPENROUTER_API_KEY: str = os.environ["OPENROUTER_API_KEY"]
ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0") or "0")
OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
DB_PATH: str = os.getenv("DB_PATH", "/root/LabDoctorM/projects/cheque-bot/cheques.db")
LOG_PATH: str = os.getenv("LOG_PATH", "/var/log/cheque-bot.log")
GOOGLE_CREDENTIALS_JSON: str = os.getenv("GOOGLE_CREDENTIALS_JSON", "")
GOOGLE_SHEET_ID: str = os.getenv("GOOGLE_SHEET_ID", "")

# Валидация обязательных полей
for _key in ("BOT_TOKEN", "OPENROUTER_API_KEY"):
    if not locals().get(_key):
        raise SystemExit(f"FATAL: Missing required env var: {_key}")
