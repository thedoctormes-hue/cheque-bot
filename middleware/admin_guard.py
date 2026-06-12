"""Middleware для проверки прав администратора."""

import os
from aiogram.types import Message, CallbackQuery
from config import ADMIN_ID


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором."""
    return user_id == ADMIN_ID


async def admin_required(message: Message) -> bool:
    """Возвращает True если пользователь — админ, иначе отправляет отказ."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return False
    return True


async def admin_required_callback(callback: CallbackQuery) -> bool:
    """Возвращает True если callback от админа, иначе отправляет отказ."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return False
    return True
