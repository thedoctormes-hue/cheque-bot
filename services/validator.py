"""Валидация ответа AI при парсинге чеков."""

from dataclasses import dataclass, field
from typing import List
from datetime import datetime


@dataclass
class ValidationResult:
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def validate_cheque(data: dict) -> ValidationResult:
    """Валидирует распознанные данные чека."""
    result = ValidationResult()

    # Проверка даты
    date_str = data.get("date")
    if not date_str:
        result.errors.append("Дата не распознана")
        result.is_valid = False
    else:
        try:
            dt = datetime.strptime(str(date_str), "%Y-%m-%d")
            if dt.year < 2020 or dt.year > 2030:
                result.warnings.append(f"Необычный год в дате: {dt.year}")
            if dt > datetime.now():
                result.errors.append("Дата чека в будущем")
                result.is_valid = False
        except ValueError:
            result.errors.append(f"Некорректный формат даты: {date_str}")
            result.is_valid = False

    # Проверка суммы
    amount = data.get("amount")
    if amount is None:
        result.errors.append("Сумма не распознана")
        result.is_valid = False
    else:
        try:
            amount_float = float(amount)
            if amount_float <= 0:
                result.errors.append(f"Сумма должна быть положительной: {amount}")
                result.is_valid = False
            elif amount_float > 100000:
                result.warnings.append(f"Очень большая сумма: {amount_float}")
        except (ValueError, TypeError):
            result.errors.append(f"Некорректная сумма: {amount}")
            result.is_valid = False

    # Проверка магазина
    shop = data.get("shop")
    if not shop or not str(shop).strip():
        result.errors.append("Магазин не распознан")
        result.is_valid = False
    elif len(str(shop)) < 2:
        result.warnings.append(f"Подозрительно короткое название магазина: {shop}")

    # Проверка категории
    valid_categories = ["продукты", "топливо", "офис", "прочее"]
    category = data.get("category")
    if not category or str(category).lower() not in valid_categories:
        result.warnings.append(f"Неизвестная категория: {category}, будет установлено 'прочее'")

    return result


def sanitize_cheque(data: dict) -> dict:
    """Очищает и нормализует данные чека."""
    cleaned = dict(data)

    # Нормализация даты
    date_str = cleaned.get("date")
    if date_str:
        try:
            for fmt in ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d"]:
                try:
                    dt = datetime.strptime(str(date_str), fmt)
                    cleaned["date"] = dt.strftime("%Y-%m-%d")
                    break
                except ValueError:
                    continue
        except Exception:
            pass

    # Нормализация суммы
    amount = cleaned.get("amount")
    if amount is not None:
        try:
            cleaned["amount"] = round(float(str(amount).replace(",", ".").replace(" ", "")), 2)
        except (ValueError, TypeError):
            pass

    # Нормализация магазина
    shop = cleaned.get("shop")
    if shop:
        cleaned["shop"] = str(shop).strip().title()

    # Нормализация категории
    valid_categories = ["продукты", "топливо", "офис", "прочее"]
    category = cleaned.get("category")
    if category and str(category).lower() in valid_categories:
        cleaned["category"] = str(category).lower()
    else:
        cleaned["category"] = "прочее"

    return cleaned
