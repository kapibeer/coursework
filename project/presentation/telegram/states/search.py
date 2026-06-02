from aiogram.fsm.state import State, StatesGroup


class FastSearchStates(StatesGroup):
    choosing_game = State()
    entering_question = State()


class DeepSearchStates(StatesGroup):
    choosing_game = State()
    entering_question = State()

