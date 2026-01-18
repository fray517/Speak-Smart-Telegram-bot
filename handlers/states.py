from aiogram.fsm.state import State
from aiogram.fsm.state import StatesGroup


class Mode(StatesGroup):
    practice_wait_answer = State()
    support_wait_question = State()
    operator_active = State()

