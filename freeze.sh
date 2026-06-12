#!/usr/bin/env bash
# freeze.sh — Заморозка cheque-bot
# Останавливает и отключает сервис, освобождает ресурсы
# Использование: bash freeze.sh

set -euo pipefail

SERVICE_NAME="cheque-bot"

echo "🧊 Cheque-Bot — Заморозка"

# 1. Останавливаем сервис
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "⏹️  Остановка $SERVICE_NAME..."
    systemctl stop "$SERVICE_NAME"
    echo "✅ Сервис остановлен"
else
    echo "ℹ️  Сервис уже остановлен"
fi

# 2. Отключаем автозапуск
if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo "🔌 Отключение автозапуска..."
    systemctl disable "$SERVICE_NAME"
    echo "✅ Автозапуск отключён"
else
    echo "ℹ️  Автозапуск уже отключён"
fi

# 3. Убиваем зависшие процессы если есть
PIDS=$(pgrep -f "cheque-bot" 2>/dev/null || true)
if [ -n "$PIDS" ]; then
    echo "💀 Убиваю зависшие процессы: $PIDS"
    kill $PIDS 2>/dev/null || true
    sleep 1
fi

# 4. Статус
echo ""
echo "📊 Статус:"
systemctl status "$SERVICE_NAME" --no-pager -l 2>/dev/null || echo "Сервис не активен"
echo ""
echo "🧊 Cheque-Bot заморожен. Для запуска: bash unfreeze.sh"
