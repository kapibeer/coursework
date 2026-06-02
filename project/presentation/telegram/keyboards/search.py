from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from domain.entities.game import BoardGame


def build_game_choice_keyboard(games: list[BoardGame]) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=game.title)] for game in games],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
