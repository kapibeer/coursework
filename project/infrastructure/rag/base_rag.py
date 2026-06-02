from collections.abc import Awaitable, Callable
import json
import unicodedata

from domain.entities.search import RagAnswer, SearchChunk


class BaseRAGService:
    def __init__(self, retriever, reranker, llm_client, min_confidence: float = 0.65) -> None:
        self.retriever = retriever
        self.reranker = reranker
        self.llm_client = llm_client
        self.min_confidence = min_confidence

    @staticmethod
    def _parse_json(raw: str) -> dict | None:
        if not raw:
            return None

        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None

        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = unicodedata.normalize("NFKC", str(text))
        return text.lower().replace("ё", "е")

    def _merge_chunks(self, chunk_groups: list[list[SearchChunk]]) -> list[SearchChunk]:
        merged: list[SearchChunk] = []
        seen: set[str] = set()

        for group in chunk_groups:
            for chunk in group:
                key = self._normalize_text(chunk.text)
                if key in seen:
                    continue
                seen.add(key)
                merged.append(chunk)

        return merged

    def _build_scope_prompt(self, game_title: str, question: str, context: str) -> str:
        return f"""
Ты проверяешь, связан ли вопрос с выбранной настольной игрой и её правилами.

Не отсекай вопрос слишком рано: если в нём есть игровые сущности, названия карт, юнитов, жетонов, локаций, фаз, ресурсов, действий или разговорное описание механики, считай его релевантным.

Только если вопрос явно не относится к выбранной игре и не похож на вопрос о её правилах, ответь:
{{
  "is_relevant": false
}}

Если вопрос относится к игре или по найденным правилам выглядит как вопрос о её правилах, ответь:
{{
  "is_relevant": true
}}

Игра:
{game_title}

Вопрос:
{question}

Найденные правила:
{context}
""".strip()

    @staticmethod
    def _out_of_scope_message() -> str:
        return (
            "Это не в моей компетенции.\n\n"
            "Задай, пожалуйста, вопрос по настольной игре, её правилам или игровой ситуации."
        )

    @staticmethod
    def _low_confidence_message() -> str:
        return (
            "Похоже, я не смог достаточно уверенно разобраться в этом фрагменте правил.\n\n"
            "Попробуй переформулировать вопрос или уточнить игровую ситуацию, и я попробую ещё раз."
        )

    def _is_confident_enough(self, enough: bool, confidence: float) -> bool:
        return enough and confidence >= self.min_confidence

    @staticmethod
    async def _notify_status(
        status_callback: Callable[[str], Awaitable[None]] | None,
        text: str,
    ) -> None:
        if status_callback is not None:
            await status_callback(text)

    async def answer(self, game_title: str, question: str, model: str, top_k: int = 5) -> RagAnswer:
        chunks = await self.retriever.search(game_title=game_title, query=question, top_k=top_k)
        context = "\n\n".join(chunk.text for chunk in chunks)
        prompt = (
            "Ты отвечаешь на вопрос по правилам настольной игры.\n"
            "Используй только информацию из контекста.\n\n"
            f"Вопрос:\n{question}\n\nКонтекст:\n{context}\n\nОтвет:"
        )
        answer = await self.llm_client.generate(prompt, model=model)
        return RagAnswer(answer=answer, chunks=chunks, used_deep_search=False)
