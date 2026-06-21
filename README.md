# Cheque-Bot 🧾

> **Владелец:** DoctorM&Ai | **Статус:** active

Telegram-бот для автоматизации бухгалтерии с AI-парсингом чеков.

Telegram-бот для автоматизации бухгалтерии с AI-парсингом чеков.

**Статус: ЗАМОРОЖЕН** (см. [TROUBLESHOOTING.md](TROUBLESHOOTING.md))

Отправьте фото чека — бот распознает дату, сумму, магазин и категорию через
OpenRouter Vision API, предложит подтвердить или исправить данные inline-кнопками.

## Возможности

- **AI-парсинг чеков** — фото → структурированные данные через OpenRouter Vision API
- **Валидация** — проверка даты, суммы, магазина, категории
- **Ручная коррекция** — inline-кнопки для исправления полей + `/cancel` для отмены
- **Отчёты** — `/report` (день), `/week` (неделя по категориям), `/month` (месяц)
- **Экспорт** — CSV за месяц через `/export`
- **Статистика** — метрики парсинга, ошибок, retries через `/stats`
- **Дедупликация** — защита от повторной обработки одного чека
- **Retry с backoff** — 3 попытки при ошибках API с экспоненциальной задержкой
- **Очередь ошибок** — фоновый воркер для повторной обработки неудачных чеков
- **Google Sheets** — опциональная синхронизация с таблицей
- **Docker** — готовый Dockerfile + docker-compose.yml
- **systemd** — автозапуск, перезапуск при падении, лимит памяти 512MB

## Стек

| Компонент       | Технология          |
|-----------------|---------------------|
| Telegram        | aiogram 3.28.2      |
| AI Vision       | OpenRouter API      |
| База данных     | SQLite              |
| Деплой          | systemd / Docker    |
| Тесты           | pytest + pytest-asyncio |
| Линтер          | ruff                |

## Быстрый старт

### Требования

- Python 3.10+
- systemd (для продакшн-деплоя)
- Токен Telegram-бота (@BotFather)
- API-ключ OpenRouter (https://openrouter.ai)

### 1. Клонирование

```bash
cd /root/LabDoctorM/projects
git clone <repo-url> cheque-bot
cd cheque-bot
```

### 2. Виртуальное окружение

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Конфигурация

```bash
cp .env.example .env
# Отредактируйте .env — заполните обязательные поля
```

Обязательные переменные:

```env
BOT_TOKEN=your_telegram_bot_token
OPENROUTER_API_KEY=your_openrouter_key
ADMIN_ID=your_telegram_id
```

Опциональные:

```env
OPENROUTER_MODEL=google/gemini-2.0-flash-001
DB_PATH=/root/LabDoctorM/projects/cheque-bot/cheques.db
LOG_PATH=/var/log/cheque-bot.log
GOOGLE_CREDENTIALS_JSON=/path/to/credentials.json
GOOGLE_SHEET_ID=your_sheet_id
```

### 4. Запуск (разработка)

```bash
source venv/bin/activate
python main.py
```

### 5. Запуск (продакшн)

```bash
# Копируем systemd unit
cp cheque-bot.service /etc/systemd/system/
systemctl daemon-reload

# Запуск и автозапуск
systemctl enable --now cheque-bot

# Проверка
systemctl status cheque-bot
journalctl -u cheque-bot -f
```

### 6. Docker

```bash
docker compose up -d
docker compose logs -f
```

## Команды бота

| Команда    | Доступ  | Описание                                    |
|------------|---------|---------------------------------------------|
| `/start`   | все     | Приветствие, инициализация БД               |
| `/help`    | все     | Инструкция                                  |
| `/cancel`  | все     | Отменить текущее действие (сбросить диалог) |
| `/report`  | админ   | Отчёт за сегодня                            |
| `/week`    | админ   | Отчёт за неделю (группировка по категориям) |
| `/month`   | админ   | Отчёт за месяц                              |
| `/export`  | админ   | Экспорт в CSV                               |
| `/stats`   | админ   | Статистика бота (метрики)                   |

## Архитектура

```
cheque-bot/
├── main.py                  # Точка входа, polling, graceful shutdown
├── config.py                # Единая конфигурация (env → константы)
├── requirements.txt         # Продакшн-зависимости
├── requirements-dev.txt     # Тесты и линтер
├── cheque-bot.service       # systemd unit
├── Dockerfile               # Multi-stage, non-root, healthcheck
├── docker-compose.yml       # Деплой через Docker
├── freeze.sh                # Заморозка (остановка)
├── unfreeze.sh              # Разморозка (быстрый запуск)
├── middleware/
│   └── admin_guard.py       # Проверка прав администратора
├── handlers/
│   ├── cheque.py            # Приём фото, парсинг, inline-коррекция, /cancel
│   └── admin.py             # /week, /month, /export, /stats
├── services/
│   ├── database.py          # SQLite: CRUD, дедупликация, миграции
│   ├── openrouter.py        # AI Vision API с retry + exponential backoff
│   ├── validator.py         # Валидация и нормализация данных
│   ├── states.py            # FSM для коррекции чека
│   ├── metrics.py           # In-memory счётчики
│   ├── queue.py             # Очередь неудачных чеков + фоновый воркер
│   ├── migrate.py           # SQLite миграции
│   └── sheets.py            # Google Sheets (lazy-safe, опционально)
└── tests/                   # 80 unit-тестов
    ├── conftest.py          # Общие фикстуры
    ├── test_cheque_handlers.py
    ├── test_admin_handlers.py
    ├── test_database.py
    ├── test_openrouter.py
    ├── test_migrate.py
    ├── test_queue.py
    └── test_new_features.py
```

## Тестирование

```bash
source venv/bin/activate
pip install -r requirements-dev.txt
pytest tests/ -v
```

80 тестов, покрытие:
- Хендлеры: start, help, photo, report, confirm, edit flow, cancel, admin commands
- Сервисы: database (CRUD, дедупликация), openrouter, validator, migrations, queue
- Безопасность: admin access control, non-admin blocked
- Новые фичи: delete, update, cancel, duplicate check

## Заморозка / Разморозка

Проект заморожен до решения заказчика. Для управления:

```bash
# Заморозить (остановить, отключить автозапуск)
bash freeze.sh

# Разморозить (проверить зависимости, запустить)
bash unfreeze.sh
```

Подробности: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

## Безопасность

- Admin guard на все отчётные команды (по `ADMIN_ID`)
- ErrorLoggingMiddleware — перехват неожиданных ошибок
- Graceful shutdown по SIGTERM/SIGINT
- RotatingFileHandler (10MB × 5 файлов)
- Docker: non-root пользователь, resource limits, healthcheck
- systemd: `NoNewPrivileges`, `ProtectSystem=strict`, `MemoryMax=512M`
- Дедупликация чеков по `message_id`

## Лицензия

MIT
