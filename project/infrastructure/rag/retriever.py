from domain.entities.search import SearchChunk
from domain.repositories.chunk_repository import ChunkRepository


class Retriever:
    def __init__(
        self,
        *,
        chunk_repository: ChunkRepository,
        embedding_client,
        default_model: str,
        default_chunking: str,
        default_chunk_size: int,
    ) -> None:
        self.chunk_repository = chunk_repository
        self.embedding_client = embedding_client
        self.default_model = default_model
        self.default_chunking = default_chunking
        self.default_chunk_size = default_chunk_size

    async def search(
        self,
        *,
        game_title: str,
        query: str,
        top_k: int,
        model_name: str | None = None,
        chunking: str | None = None,
        chunk_size: int | None = None,
    ) -> list[SearchChunk]:
        model_name = model_name or self.default_model
        chunking = chunking or self.default_chunking
        chunk_size = chunk_size or self.default_chunk_size

        vector = await self.embedding_client.embed(query, model_name)
        if vector is None:
            return []

        return await self.chunk_repository.search(
            game_title=game_title,
            query_vector=vector,
            top_k=top_k,
        )
