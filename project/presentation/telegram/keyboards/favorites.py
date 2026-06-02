from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from domain.entities.game import BoardGame


def build_favorites_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить игру", callback_data="favorites:add")],
            [InlineKeyboardButton(text="🗑️ Удалить игру", callback_data="favorites:remove")],
            [InlineKeyboardButton(text="↩️ Назад в меню", callback_data="menu:back")],
        ]
    )


def build_games_reply_keyboard(games: list[BoardGame], placeholder: str | None = None) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=game.title)] for game in games]
    if placeholder:
        rows.append([KeyboardButton(text=placeholder)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=True)


def build_game_search_results_keyboard(games: list[BoardGame]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=game.title, callback_data=f"favorites:add:{game.id}")]
        for game in games
        if game.id is not None
    ]
    buttons.append([InlineKeyboardButton(text="↩️ Назад", callback_data="favorites:open")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
