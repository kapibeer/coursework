from aiogram.fsm.state import State, StatesGroup


class AdminAddGameStates(StatesGroup):
    waiting_for_pdf = State()
    waiting_for_series_title = State()
    waiting_for_source_title = State()
    waiting_for_description = State()
    waiting_for_release_year = State()
