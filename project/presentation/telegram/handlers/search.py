import logging
import unicodedata

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from presentation.telegram.keyboards.common import build_answer_actions_keyboard, remove_reply_keyboard
from presentation.telegram.keyboards.search import build_game_choice_keyboard
from presentation.telegram.states.search import DeepSearchStates, FastSearchStates


def get_search_router(container) -> Router:
    router = Router()
    logger = logging.getLogger(__name__)

    async def _build_status_updater(status_message: Message):
        last_text = status_message.text or ""

        async def update(text: str) -> None:
            nonlocal last_text
            if text == last_text:
                return
            await status_message.edit_text(text)
            last_text = text

        return update

    async def _handle_search_error(
        status_message: Message,
        mode: str,
        game_title: str,
        exc: Exception,
    ) -> None:
        logger.exception("Search failed in %s mode for game '%s'", mode, game_title, exc_info=exc)
        await status_message.edit_text(
            "Сейчас не получается обратиться к модели 🤖\n\n"
            "Попробуй ещё раз через минуту. Если ошибка повторится, можно задать вопрос позже или выбрать другой режим поиска.",
            reply_markup=build_answer_actions_keyboard(),
        )

    def _normalize_text(text: str) -> str:
        text = unicodedata.normalize("NFKC", text or "")
        return " ".join(text.lower().replace("ё", "е").split())

    async def _match_selected_game(message: Message) -> tuple[object | None, list[object]]:
        games = await container.favorite_games_use_case.list_games(message.from_user.id)
        raw_text = (message.text or "").strip()
        normalized_text = _normalize_text(raw_text)

        exact_match = next((game for game in games if game.title == raw_text), None)
        if exact_match is not None:
            return exact_match, games

        normalized_match = next(
            (game for game in games if _normalize_text(game.title) == normalized_text),
            None,
        )
        if normalized_match is not None:
            return normalized_match, games

        fuzzy_match = next(
            (
                game
                for game in games
                if normalized_text
                and (
                    normalized_text in _normalize_text(game.title)
                    or _normalize_text(game.title).startswith(normalized_text)
                )
            ),
            None,
        )
        return fuzzy_match, games

    async def _handle_game_selection(message: Message, state: FSMContext, mode: str) -> None:
        selected, games = await _match_selected_game(message)
        if selected is None:
            available_titles = "\n".join(f"• {game.title}" for game in games) if games else "Список пуст."
            await message.answer(
                "🎲 Не удалось распознать игру. Выбери её с клавиатуры или отправь точное название.\n\n"
                f"Доступные игры:\n{available_titles}"
            )
            return

        if mode == "fast":
            await state.set_state(FastSearchStates.entering_question)
        else:
            await state.set_state(DeepSearchStates.entering_question)

        await state.update_data(game_title=selected.title, search_mode=mode)
        await message.answer(
            f"🎯 Игра выбрана: {selected.title}\nТеперь введи вопрос.",
            reply_markup=remove_reply_keyboard(),
        )

    async def _start_choose_game(
        callback: CallbackQuery,
        state: FSMContext,
        search_state,
        mode: str,
    ) -> None:
        games = await container.favorite_games_use_case.list_games(callback.from_user.id)
        if not games:
            await callback.answer("⭐ Сначала добавь игру в любимые.", show_alert=True)
            return
        await state.set_state(search_state.choosing_game)
        await state.update_data(
            search_mode=mode,
            available_game_titles=[game.title for game in games],
        )
        await callback.message.answer(
            "🎲 Выбери игру, по которой хочешь задать вопрос.",
            reply_markup=build_game_choice_keyboard(games),
        )
        await callback.answer()

    @router.callback_query(F.data == "search:fast")
    async def start_fast_search(callback: CallbackQuery, state: FSMContext) -> None:
        await _start_choose_game(callback, state, FastSearchStates, "fast")

    @router.callback_query(F.data == "search:deep")
    async def start_deep_search(callback: CallbackQuery, state: FSMContext) -> None:
        await _start_choose_game(callback, state, DeepSearchStates, "deep")

    @router.message(FastSearchStates.choosing_game)
    async def capture_selected_game_fast(message: Message, state: FSMContext) -> None:
        await _handle_game_selection(message, state, "fast")

    @router.message(DeepSearchStates.choosing_game)
    async def capture_selected_game_deep(message: Message, state: FSMContext) -> None:
        await _handle_game_selection(message, state, "deep")

    @router.message(FastSearchStates.entering_question)
    async def process_fast_search(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        game_title = data["game_title"]
        status_message = await message.answer("🔎 Рыскаю в священных писаниях этой игры…")
        status_callback = await _build_status_updater(status_message)
        try:
            answer = await container.search_use_case.fast_search(
                game_title=game_title,
                question=message.text or "",
                model=container.settings.default_generation_model,
                status_callback=status_callback,
            )
        except Exception as exc:
            await _handle_search_error(status_message, "fast", game_title, exc)
            await state.set_state(None)
            await state.update_data(last_game_title=game_title, last_search_mode="fast")
            return

        await status_message.edit_text(
            answer.answer,
            reply_markup=build_answer_actions_keyboard(),
        )
        await state.set_state(None)
        await state.update_data(last_game_title=game_title, last_search_mode="fast")

    @router.message(DeepSearchStates.entering_question)
    async def process_deep_search(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        game_title = data["game_title"]
        status_message = await message.answer("🧠 Открываю архивы и раскладываю вопрос…")
        status_callback = await _build_status_updater(status_message)
        try:
            answer = await container.search_use_case.deep_search(
                game_title=game_title,
                question=message.text or "",
                model=container.settings.default_generation_model,
                status_callback=status_callback,
            )
        except Exception as exc:
            await _handle_search_error(status_message, "deep", game_title, exc)
            await state.set_state(None)
            await state.update_data(last_game_title=game_title, last_search_mode="deep")
            return

        await status_message.edit_text(
            answer.answer,
            reply_markup=build_answer_actions_keyboard(),
        )
        await state.set_state(None)
        await state.update_data(last_game_title=game_title, last_search_mode="deep")

    @router.callback_query(F.data == "search:repeat")
    async def repeat_search(callback: CallbackQuery, state: FSMContext) -> None:
        data = await state.get_data()
        game_title = data.get("last_game_title")
        if not game_title:
            await callback.answer("⚠️ Не удалось определить игру для повторного вопроса.", show_alert=True)
            return
        mode = data.get("last_search_mode", "fast")
        if mode == "deep":
            await state.set_state(DeepSearchStates.entering_question)
        else:
            await state.set_state(FastSearchStates.entering_question)
        await state.update_data(game_title=game_title, search_mode=mode)
        await callback.message.answer(f"🎲 Задай ещё один вопрос по игре {game_title}.")
        await callback.answer()

    return router
