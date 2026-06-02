from domain.entities.user import User

from infrastructure.db.postgres.base import Database
from infrastructure.db.postgres.models import UserModel
from sqlalchemy import select


class PostgresUserRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        async with self.database.session_factory() as session:
            result = await session.execute(
                select(UserModel).where(UserModel.telegram_id == telegram_id)
            )
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return User(
                id=model.id,
                telegram_id=model.telegram_id,
                username=model.username,
                first_name=model.first_name,
                onboarded=model.onboarded,
                is_admin=model.is_admin,
                created_at=model.created_at,
            )

    async def create_or_update(self, user: User) -> User:
        async with self.database.session_factory() as session:
            result = await session.execute(
                select(UserModel).where(UserModel.telegram_id == user.telegram_id)
            )
            model = result.scalar_one_or_none()
            if model is None:
                model = UserModel(
                    telegram_id=user.telegram_id,
                    username=user.username,
                    first_name=user.first_name,
                    onboarded=user.onboarded,
                    is_admin=user.is_admin,
                )
                session.add(model)
            else:
                model.username = user.username
                model.first_name = user.first_name
                model.is_admin = user.is_admin
            await session.commit()
            await session.refresh(model)
            return User(
                id=model.id,
                telegram_id=model.telegram_id,
                username=model.username,
                first_name=model.first_name,
                onboarded=model.onboarded,
                is_admin=model.is_admin,
                created_at=model.created_at,
            )

    async def set_onboarded(self, telegram_id: int, onboarded: bool = True) -> None:
        async with self.database.session_factory() as session:
            result = await session.execute(
                select(UserModel).where(UserModel.telegram_id == telegram_id)
            )
            model = result.scalar_one_or_none()
            if model is None:
                return
            model.onboarded = onboarded
            await session.commit()
