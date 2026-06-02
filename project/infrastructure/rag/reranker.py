import asyncio

from domain.entities.search import SearchChunk


class CrossEncoderReranker:
    def __init__(self, model_path: str) -> None:
        self.model = None
        try:
            from sentence_transformers import CrossEncoder

            self.model = CrossEncoder(model_path, trust_remote_code=True, device="cpu")
        except Exception:
            self.model = None

    def _rerank_sync(self, question: str, chunks: list[SearchChunk], top_k: int) -> list[SearchChunk]:
        valid_chunks = [chunk for chunk in chunks if chunk.text.strip()]
        if not valid_chunks:
            return []
        if self.model is None:
            return valid_chunks[:top_k]

        pairs = [[question, chunk.text] for chunk in valid_chunks]
        scores = self.model.predict(pairs, batch_size=4, show_progress_bar=False)
        ranked = sorted(zip(valid_chunks, scores), key=lambda item: item[1], reverse=True)
        return [chunk for chunk, _ in ranked[:top_k]]

    async def rerank(self, question: str, chunks: list[SearchChunk], top_k: int) -> list[SearchChunk]:
        return await asyncio.to_thread(self._rerank_sync, question, chunks, top_k)
