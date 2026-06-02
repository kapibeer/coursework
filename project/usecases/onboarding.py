from domain.entities.user import User
from domain.repositories.user_repository import UserRepository


class OnboardingUseCase:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def ensure_user(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        is_admin: bool,
    ) -> User:
        user = User(
            id=None,
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            is_admin=is_admin,
        )
        return await self.user_repository.create_or_update(user)

