from collections.abc import Awaitable, Callable

from domain.entities.search import RagAnswer


class SearchUseCase:
    def __init__(self, fast_search_service, deep_search_service) -> None:
        self.fast_search_service = fast_search_service
        self.deep_search_service = deep_search_service

    async def fast_search(
        self,
        game_title: str,
        question: str,
        model: str,
        status_callback: Callable[[str], Awaitable[None]] | None = None,
    ) -> RagAnswer:
        return await self.fast_search_service.answer(
            game_title=game_title,
            question=question,
            model=model,
            status_callback=status_callback,
        )

    async def deep_search(
        self,
        game_title: str,
        question: str,
        model: str,
        status_callback: Callable[[str], Awaitable[None]] | None = None,
    ) -> RagAnswer:
        return await self.deep_search_service.answer(
            game_title=game_title,
            question=question,
            model=model,
            status_callback=status_callback,
        )
