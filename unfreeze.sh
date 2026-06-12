#!/usr/bin/env bash
# unfreeze.sh — Разморозка cheque-bot
# Запускает бота в продакшн-режиме через systemd
# Использование: bash unfreeze.sh

set -euo pipefail

PROJECT_DIR="/root/LabDoctorM/projects/cheque-bot"
SERVICE_NAME="cheque-bot"

echo "🐦‍⬛ Cheque-Bot — Разморозка"

# 1. Проверяем .env
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "❌ Нет .env файла в $PROJECT_DIR"
    exit 1
fi

# 2. Проверяем venv
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "📦 Создаю venv..."
    python3 -m venv "$PROJECT_DIR/venv"
    source "$PROJECT_DIR/venv/bin/activate"
    pip install -r "$PROJECT_DIR/requirements.txt"
else
    source "$PROJECT_DIR/venv/bin/activate"
fi

# 3. Быстрый тест — импорты работают
echo "🔍 Проверка зависимостей..."
python3 -c "
import aiogram, openai, dotenv, config
from services.database import init_db
from services.openrouter import parse_cheque
from handlers.cheque import handle_start
print('OK: все импорты загружены')
"

# 4. Запускаем сервис
echo "🚀 Запуск $SERVICE_NAME..."
systemctl enable "$SERVICE_NAME"
systemctl start "$SERVICE_NAME"

# 5. Проверяем что поднялся
sleep 2
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "✅ Cheque-Bot запущен!"
    systemctl status "$SERVICE_NAME" --no-pager -l
else
    echo "❌ Сервис не поднялся. Логи:"
    journalctl -u "$SERVICE_NAME" --no-pager -n 20
    exit 1
fi
