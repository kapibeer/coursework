from domain.entities.game import BoardGame
from domain.repositories.favorite_repository import FavoriteRepository
from domain.repositories.game_repository import GameRepository


class FavoriteGamesUseCase:
    def __init__(
        self,
        favorite_repository: FavoriteRepository,
        game_repository: GameRepository,
    ) -> None:
        self.favorite_repository = favorite_repository
        self.game_repository = game_repository

    async def add_game(self, telegram_id: int, game_id: int) -> None:
        await self.favorite_repository.add_favorite(telegram_id, game_id)

    async def remove_game(self, telegram_id: int, game_id: int) -> None:
        await self.favorite_repository.remove_favorite(telegram_id, game_id)

    async def list_games(self, telegram_id: int) -> list[BoardGame]:
        favorite_ids = await self.favorite_repository.list_favorite_ids(telegram_id)
        games: list[BoardGame] = []
        for game_id in favorite_ids:
            game = await self.game_repository.get_by_id(game_id)
            if game:
                games.append(game)
        return games

