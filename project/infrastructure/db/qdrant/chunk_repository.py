import asyncio
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from domain.entities.search import SearchChunk
from infrastructure.config.settings import Settings


COLLECTION_NAME = "games_chunks_gemini_embedding_001"
VECTOR_SIZE = 3072


class QdrantChunkRepository:
    def __init__(self, settings: Settings) -> None:
        self.client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)

    async def search(
        self,
        *,
        game_title: str,
        query_vector: list[float],
        top_k: int,
    ) -> list[SearchChunk]:
        result = await asyncio.to_thread(
            self.client.query_points,
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=top_k,
            query_filter=Filter(
                must=[
                    FieldCondition(key="game", match=MatchValue(value=game_title)),
                ]
            ),
            with_payload=True,
        )
        return [
            SearchChunk(
                text=self._format_chunk_text(point.payload or {}),
                score=point.score,
                payload=point.payload,
            )
            for point in result.points
        ]

    async def ensure_collection(self) -> None:
        if await asyncio.to_thread(self.client.collection_exists, COLLECTION_NAME):
            return

        await asyncio.to_thread(
            self.client.create_collection,
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )

    async def delete_source_chunks(
        self,
        *,
        game_title: str,
        source_title: str,
    ) -> None:
        if not await asyncio.to_thread(self.client.collection_exists, COLLECTION_NAME):
            return

        await asyncio.to_thread(
            self.client.delete,
            collection_name=COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(key="game", match=MatchValue(value=game_title)),
                    FieldCondition(key="source_title", match=MatchValue(value=source_title)),
                ]
            ),
        )

    async def upsert_chunks(
        self,
        *,
        game_title: str,
        source_title: str,
        document_name: str,
        release_year: int | None,
        texts: list[str],
        search_texts: list[str],
        vectors: list[list[float]],
    ) -> None:
        points = [
            PointStruct(
                id=str(uuid4()),
                vector=vector,
                payload={
                    "game": game_title,
                    "source_title": source_title,
                    "document_name": document_name,
                    "release_year": release_year,
                    "text": text,
                    "search_text": search_text,
                },
            )
            for text, search_text, vector in zip(texts, search_texts, vectors, strict=False)
        ]
        if not points:
            return

        await asyncio.to_thread(self.client.upsert, collection_name=COLLECTION_NAME, points=points, wait=True)

    @staticmethod
    def _format_chunk_text(payload: dict) -> str:
        raw_text = (payload.get("text", "") or "").strip()
        source_title = (payload.get("source_title", "") or "").strip()
        if not source_title:
            return raw_text
        return f"[Источник: {source_title}]\n{raw_text}".strip()
