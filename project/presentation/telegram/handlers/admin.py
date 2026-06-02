from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from presentation.telegram.states.admin import AdminAddGameStates


def get_admin_router(container) -> Router:
    router = Router()
    uploads_dir = Path("project/uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)

    def _is_admin(telegram_id: int) -> bool:
        return telegram_id in container.settings.admin_telegram_ids

    @router.message(F.text == "/admin")
    async def start_admin(message: Message) -> None:
        if not _is_admin(message.from_user.id):
            return
        await message.answer("🛠️ Админ-режим: отправь PDF-файл, чтобы добавить источник в серию игр.")

    @router.message(F.document)
    async def accept_pdf(message: Message, state: FSMContext) -> None:
        if not _is_admin(message.from_user.id):
            return
        if message.document.mime_type != "application/pdf":
            await message.answer("📄 Нужен именно PDF-файл.")
            return
        file = await message.bot.get_file(message.document.file_id)
        destination = uploads_dir / message.document.file_name
        await message.bot.download_file(file.file_path, destination=destination)
        await state.set_state(AdminAddGameStates.waiting_for_series_title)
        await state.update_data(pdf_path=str(destination), pdf_name=message.document.file_name)
        await message.answer("📄 PDF сохранён. Теперь введи название серии.")

    @router.message(AdminAddGameStates.waiting_for_series_title)
    async def capture_series_title(message: Message, state: FSMContext) -> None:
        await state.update_data(series_title=message.text or "")
        await state.set_state(AdminAddGameStates.waiting_for_source_title)
        await message.answer("🗂️ Теперь введи название игры, дополнения или файла-источника.")

    @router.message(AdminAddGameStates.waiting_for_source_title)
    async def capture_source_title(message: Message, state: FSMContext) -> None:
        await state.update_data(source_title=message.text or "")
        await state.set_state(AdminAddGameStates.waiting_for_description)
        await message.answer("✍️ Теперь введи краткое описание этого источника.")

    @router.message(AdminAddGameStates.waiting_for_description)
    async def capture_description(message: Message, state: FSMContext) -> None:
        await state.update_data(description=message.text or "")
        await state.set_state(AdminAddGameStates.waiting_for_release_year)
        await message.answer("📅 Теперь введи год выпуска этого источника или напиши 0, если его не указывать.")

    @router.message(AdminAddGameStates.waiting_for_release_year)
    async def capture_release_year(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        year_raw = (message.text or "").strip()
        if not year_raw.isdigit():
            await message.answer("⚠️ Год должен быть числом. Попробуй ещё раз.")
            return
        release_year = int(year_raw)
        release_year = None if release_year == 0 else release_year
        game = await container.game_catalog_use_case.ensure_game(
            title=data["series_title"],
            description=data["description"],
            release_year=release_year,
        )
        await container.game_repository.add_document(
            game_id=game.id,
            source_title=data["source_title"],
            description=data["description"],
            release_year=release_year,
            file_name=data["pdf_name"],
            file_path=data["pdf_path"],
        )
        status_message = await message.answer("📚 Источник сохранён. Начинаю извлекать текст и индексировать правила.")
        try:
            await container.ingestion_service.ingest(
                pdf_path=data["pdf_path"],
                game_title=game.title,
                source_title=data["source_title"],
                release_year=release_year,
            )
        except Exception as exc:
            await status_message.edit_text(
                "⚠️ Серия и источник сохранены, но автоматическая индексация пока не завершилась.\n"
                f"Ошибка: {exc}"
            )
            await state.clear()
            return

        await state.clear()
        await status_message.edit_text(
            "✅ Источник успешно добавлен и проиндексирован.\n"
            "Теперь серия будет использоваться в поиске с учётом всех загруженных файлов."
        )

    return router
