from domain.entities.game import BoardGame
from domain.repositories.game_repository import GameRepository


class GameCatalogUseCase:
    def __init__(self, game_repository: GameRepository) -> None:
        self.game_repository = game_repository

    async def search_games(self, query: str, limit: int = 5) -> list[BoardGame]:
        return await self.game_repository.search_by_title(query, limit=limit)

    async def ensure_game(self, title: str, description: str, release_year: int | None) -> BoardGame:
        existing = await self.game_repository.get_by_title(title)
        if existing is not None:
            return existing

        return await self.game_repository.create(
            BoardGame(
                id=None,
                title=title,
                description=description,
                release_year=release_year,
            )
        )
