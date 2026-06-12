"""In-memory метрики бота."""

cheques_parsed: int = 0
cheques_saved: int = 0
ai_errors: int = 0
api_retries: int = 0


def get_stats() -> dict:
    return {
        "parsed": cheques_parsed,
        "saved": cheques_saved,
        "ai_errors": ai_errors,
        "api_retries": api_retries,
    }


def reset():
    global cheques_parsed, cheques_saved, ai_errors, api_retries
    cheques_parsed = 0
    cheques_saved = 0
    ai_errors = 0
    api_retries = 0
