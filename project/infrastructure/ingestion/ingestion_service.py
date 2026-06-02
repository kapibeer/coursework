import asyncio


class GameIngestionService:
    def __init__(
        self,
        pdf_extractor,
        layout_segmenter,
        chunker,
        embedding_client,
        chunk_repository,
        *,
        model_name: str,
        chunking: str,
        chunk_size: int,
    ) -> None:
        self.pdf_extractor = pdf_extractor
        self.layout_segmenter = layout_segmenter
        self.chunker = chunker
        self.embedding_client = embedding_client
        self.chunk_repository = chunk_repository
        self.model_name = model_name
        self.chunking = chunking
        self.chunk_size = chunk_size

    async def ingest(self, pdf_path: str, game_title: str, source_title: str, release_year: int | None) -> None:
        elements = await asyncio.to_thread(self.pdf_extractor.extract, pdf_path)
        if not elements:
            raise ValueError("PDF extraction returned no readable elements")

        segmented = await asyncio.to_thread(self.layout_segmenter.segment, elements)
        chunks = await asyncio.to_thread(self.chunker.chunk, segmented, chunk_size=self.chunk_size)
        if not chunks:
            raise ValueError("Chunking returned no chunks")

        await self.chunk_repository.ensure_collection()
        await self.chunk_repository.delete_source_chunks(
            game_title=game_title,
            source_title=source_title,
        )

        search_texts = [
            self._build_search_text(
                game_title=game_title,
                source_title=source_title,
                release_year=release_year,
                chunk_text=text,
            )
            for text in chunks
        ]

        vectors = await self.embedding_client.embed_batch(search_texts, self.model_name)
        valid_pairs = [
            (text, search_text, vector)
            for text, search_text, vector in zip(chunks, search_texts, vectors, strict=False)
            if vector is not None
        ]
        if not valid_pairs:
            raise ValueError("Failed to build embeddings for extracted chunks")

        await self.chunk_repository.upsert_chunks(
            game_title=game_title,
            source_title=source_title,
            document_name=pdf_path.split("/")[-1],
            release_year=release_year,
            texts=[text for text, _, _ in valid_pairs],
            search_texts=[search_text for _, search_text, _ in valid_pairs],
            vectors=[vector for _, _, vector in valid_pairs],
        )

    @staticmethod
    def _build_search_text(game_title: str, source_title: str, release_year: int | None, chunk_text: str) -> str:
        year_line = f"Год: {release_year}\n" if release_year is not None else ""
        return (
            f"Серия: {game_title}\n"
            f"Источник: {source_title}\n"
            f"{year_line}\n"
            f"{chunk_text}"
        ).strip()
