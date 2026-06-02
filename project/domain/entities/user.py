from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class User:
    id: int | None
    telegram_id: int
    username: str | None
    first_name: str | None
    onboarded: bool = False
    is_admin: bool = False
    created_at: datetime | None = None

