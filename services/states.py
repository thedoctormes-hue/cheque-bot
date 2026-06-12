"""FSM состояния для диалога коррекции чека."""

from aiogram.fsm.state import State, StatesGroup


class ChequeCorrection(StatesGroup):
    waiting_for_field = State()  # Ждём выбора поля для редактирования
    waiting_for_value = State()  # Ждём ввода нового значения
