from typing import Protocol

from domain.entities.game import BoardGame


class GameRepository(Protocol):
    async def get_by_id(self, game_id: int) -> BoardGame | None: ...
    async def search_by_title(self, query: str, limit: int = 5) -> list[BoardGame]: ...
    async def create(self, game: BoardGame) -> BoardGame: ...
    async def get_by_title(self, title: str) -> BoardGame | None: ...
    async def list_favorites_for_user(self, user_id: int) -> list[BoardGame]: ...
    async def add_document(
        self,
        game_id: int,
        source_title: str,
        description: str,
        release_year: int | None,
        file_name: str,
        file_path: str,
    ) -> None: ...
