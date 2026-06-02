from infrastructure.db.postgres.base import Database
from infrastructure.db.postgres.models import FavoriteGameModel, UserModel
from sqlalchemy import delete, select


class PostgresFavoriteGameRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def add_favorite(self, telegram_id: int, game_id: int) -> None:
        async with self.database.session_factory() as session:
            result = await session.execute(
                select(UserModel).where(UserModel.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            if user is None:
                return

            existing = await session.execute(
                select(FavoriteGameModel).where(
                    FavoriteGameModel.user_id == user.id,
                    FavoriteGameModel.game_id == game_id,
                )
            )
            if existing.scalar_one_or_none() is None:
                session.add(FavoriteGameModel(user_id=user.id, game_id=game_id))
                await session.commit()

    async def remove_favorite(self, telegram_id: int, game_id: int) -> None:
        async with self.database.session_factory() as session:
            result = await session.execute(
                select(UserModel).where(UserModel.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            if user is None:
                return
            await session.execute(
                delete(FavoriteGameModel).where(
                    FavoriteGameModel.user_id == user.id,
                    FavoriteGameModel.game_id == game_id,
                )
            )
            await session.commit()

    async def list_favorite_ids(self, telegram_id: int) -> list[int]:
        async with self.database.session_factory() as session:
            result = await session.execute(
                select(UserModel).where(UserModel.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            if user is None:
                return []
            favorites = await session.execute(
                select(FavoriteGameModel.game_id)
                .where(FavoriteGameModel.user_id == user.id)
                .order_by(FavoriteGameModel.game_id.asc())
            )
            return list(favorites.scalars().all())
