from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove


def build_answer_actions_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад в меню", callback_data="menu:back")],
            [InlineKeyboardButton(text="Задать еще вопрос по этой игре", callback_data="search:repeat")],
        ]
    )


def remove_reply_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()

