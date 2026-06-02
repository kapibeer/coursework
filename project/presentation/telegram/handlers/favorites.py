from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from presentation.telegram.keyboards.common import remove_reply_keyboard
from presentation.telegram.keyboards.favorites import (
    build_favorites_menu_keyboard,
    build_game_search_results_keyboard,
    build_games_reply_keyboard,
)
from presentation.telegram.states.favorites import FavoriteGameStates


def get_favorites_router(container) -> Router:
    router = Router()

    async def _render_favorites(callback: CallbackQuery) -> None:
        games = await container.favorite_games_use_case.list_games(callback.from_user.id)
        game_lines = "\n".join(f"• {game.title}" for game in games) if games else "Пока нет любимых игр."
        await callback.message.edit_text(
            f"⭐ Любимые игры:\n{game_lines}",
            reply_markup=build_favorites_menu_keyboard(),
        )
        await callback.answer()

    @router.callback_query(F.data == "favorites:open")
    async def open_favorites(callback: CallbackQuery) -> None:
        await _render_favorites(callback)

    @router.callback_query(F.data == "favorites:add")
    async def ask_game_query(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(FavoriteGameStates.entering_query)
        await callback.message.answer("➕ Введи название игры, которую хочешь добавить.")
        await callback.answer()

    @router.message(FavoriteGameStates.entering_query)
    async def search_games_for_add(message: Message, state: FSMContext) -> None:
        games = await container.game_catalog_use_case.search_games(message.text or "", limit=5)
        if not games:
            await message.answer("🔍 Игры не найдены, попробуй другое название.")
            return
        await message.answer(
            "🎯 Выбери игру из найденных вариантов:",
            reply_markup=build_game_search_results_keyboard(games),
        )
        await state.clear()

    @router.callback_query(F.data.startswith("favorites:add:"))
    async def add_favorite(callback: CallbackQuery) -> None:
        game_id = int(callback.data.split(":")[-1])
        await container.favorite_games_use_case.add_game(callback.from_user.id, game_id)
        await _render_favorites(callback)

    @router.callback_query(F.data == "favorites:remove")
    async def ask_remove(callback: CallbackQuery, state: FSMContext) -> None:
        games = await container.favorite_games_use_case.list_games(callback.from_user.id)
        if not games:
            await callback.answer("⭐ Список любимых игр пока пуст.", show_alert=True)
            return
        await state.set_state(FavoriteGameStates.deleting_game)
        await callback.message.answer(
            "🗑️ Выбери игру, которую нужно удалить.",
            reply_markup=build_games_reply_keyboard(games, placeholder="Отмена"),
        )
        await callback.answer()

    @router.message(FavoriteGameStates.deleting_game)
    async def remove_favorite(message: Message, state: FSMContext) -> None:
        if (message.text or "").strip().lower() == "отмена":
            await state.clear()
            await message.answer("↩️ Удаление отменено.", reply_markup=remove_reply_keyboard())
            return
        games = await container.favorite_games_use_case.list_games(message.from_user.id)
        match = next((game for game in games if game.title == message.text), None)
        if match is None or match.id is None:
            await message.answer("⚠️ Не удалось найти такую игру в любимых.")
            return
        await container.favorite_games_use_case.remove_game(message.from_user.id, match.id)
        await state.clear()
        remaining = await container.favorite_games_use_case.list_games(message.from_user.id)
        lines = "\n".join(f"• {game.title}" for game in remaining) if remaining else "Пока нет любимых игр."
        await message.answer(
            f"⭐ Любимые игры:\n{lines}",
            reply_markup=remove_reply_keyboard(),
        )
        await message.answer(reply_markup=build_favorites_menu_keyboard(), text="Выбери действие:")

    return router
