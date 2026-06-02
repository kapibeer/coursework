from typing import Protocol

from domain.entities.user import User


class UserRepository(Protocol):
    async def get_by_telegram_id(self, telegram_id: int) -> User | None: ...
    async def create_or_update(self, user: User) -> User: ...
    async def set_onboarded(self, telegram_id: int, onboarded: bool = True) -> None: ...

