from aiogram.fsm.state import State, StatesGroup


class FavoriteGameStates(StatesGroup):
    entering_query = State()
    deleting_game = State()

