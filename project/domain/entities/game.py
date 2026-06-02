from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class BoardGame:
    id: int | None
    title: str
    description: str
    release_year: int | None
    created_at: datetime | None = None

