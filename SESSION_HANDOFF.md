---
description: "🧾 Передача сессии ChequeBot"
type: handoff
last_reviewed: 2026-05-27
status: active
---
# 🔄 SESSION HANDOFF — ChequeBot

**Дата:** 2026-05-27
**Статус:** 🟢 Активен
**Тип:** dashboard

## 📊 TL;DR
Telegram бот для автоматизации бухгалтерии с AI парсингом чеков. Пользователь отправляет чек → бот распознаёт товары через OpenAI → записывает в БД + Google Sheets.

## Технологический стек
- Python 3, aiogram 3.4.1, OpenAI API, Google Sheets API, pandas, aiohttp
- SQLite (cheques.db)

## Что работает ✅
- Telegram bot (aiogram) — принимает чеки, парсит через OpenRouter/OpenAI
- Google Sheets интеграция — запись расходов
- Systemd автозапуск (`cheque-bot.service`, **active**)
- Тесты: `tests/` (handlers, database, openrouter)

## Структура
```
handlers/cheque.py    # Обработчики Telegram
services/database.py  # SQLite БД
services/openrouter.py # AI парсинг
services/sheets.py    # Google Sheets
main.py               # Точка входа
cheque-bot.service    # Systemd unit
```

## ⚠️ Известные проблемы
- Нет README.md
- Нет SESSION_HANDOFF (создан впервые)

## Открытые задачи
- Добавить README.md
- Расширить тесты
- Обработка ошибок AI парсинга
