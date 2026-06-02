from domain.entities.game import BoardGame

from infrastructure.db.postgres.base import Database
from infrastructure.db.postgres.models import FavoriteGameModel, GameDocumentModel, GameModel
from sqlalchemy import delete, func, select


class PostgresGameRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def get_by_id(self, game_id: int) -> BoardGame | None:
        async with self.database.session_factory() as session:
            result = await session.execute(select(GameModel).where(GameModel.id == game_id))
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return BoardGame(
                id=model.id,
                title=model.title,
                description=model.description,
                release_year=model.release_year,
                created_at=model.created_at,
            )

    async def get_by_title(self, title: str) -> BoardGame | None:
        async with self.database.session_factory() as session:
            result = await session.execute(select(GameModel).where(GameModel.title == title))
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return BoardGame(
                id=model.id,
                title=model.title,
                description=model.description,
                release_year=model.release_year,
                created_at=model.created_at,
            )

    async def search_by_title(self, query: str, limit: int = 5) -> list[BoardGame]:
        pattern = f"%{query.lower()}%"
        async with self.database.session_factory() as session:
            result = await session.execute(
                select(GameModel)
                .where(func.lower(GameModel.title).like(pattern))
                .order_by(GameModel.title.asc())
                .limit(limit)
            )
            models = result.scalars().all()
            return [
                BoardGame(
                    id=model.id,
                    title=model.title,
                    description=model.description,
                    release_year=model.release_year,
                    created_at=model.created_at,
                )
                for model in models
            ]

    async def create(self, game: BoardGame) -> BoardGame:
        async with self.database.session_factory() as session:
            model = GameModel(
                title=game.title,
                description=game.description,
                release_year=game.release_year,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return BoardGame(
                id=model.id,
                title=model.title,
                description=model.description,
                release_year=model.release_year,
                created_at=model.created_at,
            )

    async def list_favorites_for_user(self, user_id: int) -> list[BoardGame]:
        async with self.database.session_factory() as session:
            result = await session.execute(
                select(GameModel)
                .join(FavoriteGameModel, FavoriteGameModel.game_id == GameModel.id)
                .where(FavoriteGameModel.user_id == user_id)
                .order_by(GameModel.title.asc())
            )
            models = result.scalars().all()
            return [
                BoardGame(
                    id=model.id,
                    title=model.title,
                    description=model.description,
                    release_year=model.release_year,
                    created_at=model.created_at,
                )
                for model in models
            ]

    async def add_document(
        self,
        game_id: int,
        source_title: str,
        description: str,
        release_year: int | None,
        file_name: str,
        file_path: str,
    ) -> None:
        async with self.database.session_factory() as session:
            await session.execute(
                delete(GameDocumentModel).where(
                    GameDocumentModel.game_id == game_id,
                    GameDocumentModel.source_title == source_title,
                )
            )
            model = GameDocumentModel(
                game_id=game_id,
                source_title=source_title,
                description=description,
                release_year=release_year,
                file_name=file_name,
                file_path=file_path,
            )
            session.add(model)
            await session.commit()
