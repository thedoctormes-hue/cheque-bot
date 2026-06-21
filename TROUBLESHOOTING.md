# Cheque-Bot — Руководство по эксплуатации

## Статус проекта

**ЗАМОРОЖЕН** (04.06.2026) — ожидает решения заказчика.
Код готов, 80 тестов зелёные, продакшн-зависимости на месте.

---

## Диагностика: "Чек-бот не работает!!!"

### Шаг 1: Проверить статус сервиса

```bash
systemctl status cheque-bot
```

**Ожидаемый результат если заморожен:**
```
● cheque-bot.service - Cheque Accounting Bot
 Loaded: loaded (/etc/systemd/system/cheque-bot.service; disabled)
 Active: inactive (dead)
```

**Ожидаемый результат если работает:**
```
● cheque-bot.service - Cheque Accounting Bot
 Loaded: loaded (/etc/systemd/system/cheque-bot.service; enabled)
 Active: active (running)
 Main PID: <число>
 Memory: XX.XM
```

### Шаг 2: Если не работает — проверить причину

**Вариант A: Сервис остановлен (заморожен)**
```
Active: inactive (dead)
```
→ Это нормально. Проект заморожен. Для запуска: `bash unfreeze.sh`

**Вариант B: Сервис упал с ошибкой**
```
Active: failed (Result: exit-code)
```
→ Смотрим логи:
```bash
journalctl -u cheque-bot --no-pager -n 50
```

**Вариант C: Сервис крутится, но бот не отвечает**
```bash
# Проверяем что процесс жив
ps aux | grep cheque-bot

# Проверяем сеть (Telegram API доступен?)
curl -s https://api.telegram.org/bot<TOKEN>/getMe

# Проверяем OpenRouter API
curl -s https://openrouter.ai/api/v1/models \
 -H "Authorization: Bearer $OPENROUTER_API_KEY"
```

### Шаг 3: Проверить логи

```bash
# Логи systemd
journalctl -u cheque-bot -f

# Логи приложения (если настроен LOG_PATH)
tail -f /var/log/cheque-bot.log
```

### Шаг 4: Проверить .env

```bash
cat /root/LabDoctorM/projects/cheque-bot/.env
```

Обязательные поля: `BOT_TOKEN`, `OPENROUTER_API_KEY`, `ADMIN_ID`.

Если `.env` отсутствует:
```bash
cp .env.example .env
# Заполнить вручную
```

---

## Управление жизненным циклом

### Запуск (разморозка)

```bash
cd /root/LabDoctorM/projects/cheque-bot
bash unfreeze.sh
```

Скрипт автоматически:
1. Проверяет `.env`
2. Создаёт `venv` если нет
3. Проверяет импорты
4. Запускает systemd сервис
5. Ждёт 2 секунды и проверяет что поднялся

**Время запуска:** ~5 секунд.

### Остановка (заморозка)

```bash
bash freeze.sh
```

Скрипт автоматически:
1. Останавливает сервис
2. Отключает автозапуск
3. Убивает зависшие процессы

**Освобождает:** ~144MB RAM.

### Перезапуск

```bash
systemctl restart cheque-bot
```

### Проверка работоспособности

```bash
systemctl is-active cheque-bot # Должно вернуть: active
systemctl is-enabled cheque-bot # Должно вернуть: enabled
```

---

## Тесты

```bash
cd /root/LabDoctorM/projects/cheque-bot
source venv/bin/activate
pip install -r requirements-dev.txt
pytest tests/ -v
```

**Ожидаемый результат:** `80 passed`

Если тесты падают:
1. Проверьте что venv активирован: `which python`
2. Проверьте что зависимости установлены: `pip list | grep pytest`
3. Проверьте что `.env` существует с `ADMIN_ID`

---

## Структура базы данных

```bash
sqlite3 /root/LabDoctorM/projects/cheque-bot/cheques.db
```

```sql
-- Посмотреть таблицы
.tables

-- Посмотреть схему
.schema cheques

-- Последние 10 чеков
SELECT * FROM cheques ORDER BY created_at DESC LIMIT 10;

-- Количество чеков
SELECT COUNT(*) FROM cheques;

-- Сумма за сегодня
SELECT SUM(amount) FROM cheques WHERE date = date('now');
```

**Важно:** База данных сохраняется при заморозке. Данные не теряются.

---

## Очередь ошибок

Неудачные чеки складываются в `/tmp/cheque_queue/`.

```bash
# Проверить очередь
ls -la /tmp/cheque_queue/

# Очистить вручную (если нужно)
rm -rf /tmp/cheque_queue/
```

Очередь обрабатывается фоновым воркером каждые 60 секунд.
Максимум 3 попытки, потом задача удаляется.

---

## Частые проблемы

### "ModuleNotFoundError: No module named 'openai'"

```bash
cd /root/LabDoctorM/projects/cheque-bot
source venv/bin/activate
pip install -r requirements.txt
```

### "FATAL: Missing required env vars: BOT_TOKEN"

```bash
# Создать .env из шаблона
cp .env.example .env
# Или скопировать из бэкапа
```

### "Сервис запускается и сразу падает"

```bash
# Смотрим ошибку
journalctl -u cheque-bot --no-pager -n 30

# Частые причины:
# 1. Неправильный BOT_TOKEN — проверить через @BotFather
# 2. Нет доступа к OpenRouter — проверить API ключ
# 3. Нет прав на запись в DB_PATH — chmod 755 директорию
```

### "Бот отвечает, но AI не распознаёт"

```bash
# Проверить OpenRouter ключ
curl -s https://openrouter.ai/api/v1/models \
 -H "Authorization: Bearer $(grep OPENROUTER_API_KEY .env | cut -d= -f2)" \
 | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Доступно моделей: {len(d[\"data\"])}')"
```

---

## Контакты и эскалация

| Проблема | Кому идти |
|----------|-----------|
| Бот не отвечает | Сначала `journalctl -u cheque-bot`, потом к разработчику |
| Нужна новая фича | К Ворону (agent raven) |
| Проблемы с сервером | К ЗавЛабу |
| Вопросы по коду | `README.md` → `ARCHITECTURE.md` (если есть) |
