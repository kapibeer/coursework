from typing import Protocol

from domain.entities.search import SearchChunk


class ChunkRepository(Protocol):
    async def search(
        self,
        *,
        game_title: str,
        query_vector: list[float],
        top_k: int,
    ) -> list[SearchChunk]: ...
