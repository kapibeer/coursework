from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def build_main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Любимые игры", callback_data="favorites:open")],
            [InlineKeyboardButton(text="⚡ Fast search", callback_data="search:fast")],
            [InlineKeyboardButton(text="🧠 Deep search", callback_data="search:deep")],
        ]
    )
