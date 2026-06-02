from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from presentation.telegram.keyboards.menu import build_main_menu_keyboard


def get_menu_router(container) -> Router:
    router = Router()

    @router.message(CommandStart())
    async def handle_start(message: Message) -> None:
        is_admin = message.from_user.id in container.settings.admin_telegram_ids
        user = await container.onboarding_use_case.ensure_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            is_admin=is_admin,
        )
        if not user.onboarded:
            await container.user_repository.set_onboarded(message.from_user.id, True)
        text = (
            "Привет! 🎲 Я помогу найти ответ в правилах настольных игр.\n\n"
            "Для начала добавь любимые игры ⭐ или сразу перейди к поиску."
            if not user.onboarded
            else "🏰 Главное меню"
        )
        await message.answer(
            text,
            reply_markup=build_main_menu_keyboard(),
        )

    @router.callback_query(F.data == "menu:back")
    async def back_to_menu(callback: CallbackQuery) -> None:
        await callback.message.edit_text(
            "🏰 Главное меню",
            reply_markup=build_main_menu_keyboard(),
        )
        await callback.answer()

    return router
