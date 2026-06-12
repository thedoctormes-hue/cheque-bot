"""OpenRouter Vision API сервис для парсинга чеков с retry."""

import json
import base64
import asyncio
import logging
from openai import AsyncOpenAI, APIError, APITimeoutError, RateLimitError

import config as cfg
from services import metrics

logger = logging.getLogger(__name__)

_client = None

MAX_RETRIES = 3
BASE_DELAY = 1.0  # секунды


def _get_client():
    """Lazy-инициализация клиента."""
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=cfg.OPENROUTER_API_KEY,
            base_url=cfg.OPENROUTER_BASE_URL,
        )
    return _client


def _extract_json(text: str) -> dict:
    """Извлекает JSON из ответа AI (может быть обёрнут в markdown)."""
    text = text.strip()
    # Убираем markdown обёртку
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse AI response as JSON: {text[:200]}")
        return {}


async def parse_cheque(image_path: str) -> dict:
    """Парсит чек через AI с retry и exponential backoff.

    Returns:
        {date, amount, shop, category} — пустой dict при полном провале.
    """
    model = cfg.OPENROUTER_MODEL
    prompt = (
        "Распознай данные с чека и верни только JSON:\n"
        '{\n'
        '  "date": "дата в формате YYYY-MM-DD",\n'
        '  "amount": число (сумма),\n'
        '  "shop": "название магазина",\n'
        '  "category": "категория (продукты, топливо, офис, прочее)"\n'
        '}\n'
    )

    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    client = _get_client()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}},
                    ],
                }],
                timeout=30,
            )
            content = response.choices[0].message.content.strip()
            result = _extract_json(content)
            if result:
                if attempt > 1:
                    metrics.api_retries += 1
                return result
            raise ValueError(f"Empty or unparseable AI response: {content[:100]}")

        except (APITimeoutError, RateLimitError, APIError) as e:
            delay = BASE_DELAY * (2 ** (attempt - 1))
            logger.warning(f"AI API error (attempt {attempt}/{MAX_RETRIES}): {e}, retrying in {delay}s")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(delay)
            else:
                logger.error(f"AI API failed after {MAX_RETRIES} attempts: {e}")
                metrics.ai_errors += 1
                return {}

        except Exception as e:
            logger.error(f"Unexpected error in parse_cheque: {e}", exc_info=True)
            metrics.ai_errors += 1
            return {}

    return {}
