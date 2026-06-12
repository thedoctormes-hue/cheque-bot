# ── Stage 1: Builder ───────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Runtime ───────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Non-root пользователь
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Копируем зависимости из builder
COPY --from=builder /install /usr/local

# Копируем код
COPY . .

# Директории для данных
RUN mkdir -p /app/data /app/logs && chown -R appuser:appuser /app

# Healthcheck
HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
    CMD python -c "import os; exit(0 if os.path.exists('/app/main.py') else 1)"

VOLUME ["/app/data", "/app/logs"]

ENV DB_PATH=/app/data/cheques.db
ENV LOG_PATH=/app/logs/cheque-bot.log
ENV PYTHONUNBUFFERED=1

USER appuser

CMD ["python", "main.py"]
