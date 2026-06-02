from collections.abc import Awaitable, Callable

from domain.entities.search import RagAnswer, SearchChunk
from infrastructure.rag.base_rag import BaseRAGService


class FastSearchService(BaseRAGService):

    def _build_sufficiency_prompt(self, question: str, context: str) -> str:
        return f"""
Ты проверяешь, достаточно ли найденного контекста, чтобы ответить на вопрос по правилам настольной игры.

Ответь только JSON:
{{
  "enough_context": true,
  "confidence": 0.0,
  "clarifying_queries": []
}}

или

{{
  "enough_context": false,
  "confidence": 0.0,
  "clarifying_queries": ["...", "..."]
}}

Если контекста не хватает, сформулируй 1-3 коротких уточняющих поисковых запроса.

Вопрос:
{question}

Контекст:
{context}
""".strip()

    def _build_answer_prompt(self, question: str, context: str) -> str:
        return f"""
Ты отвечаешь на вопрос по правилам настольной игры.

Используй только информацию ниже.
Не придумывай ничего от себя.
Перед ответом сопоставь правило, сущности и порядок действий.
Если информации недостаточно, так и напиши.
Вообще не используй в финальном ответе слово "контекст", вместо него используй слово "правила".
Если на вопрос можно ответить кратко, то сначала пиши краткий ответ, а потом ниже минимальное необходимое пояснение.
Если на вопрос нельзя ответить кратко, то ответь одним ответом без разделений.
Можно кратко пересказать правило своими словами при необходимости.
Используй термины из правил и называй игровые сущности так, как они названы в игре.
Цитату добавляй только если она действительно помогает снять неоднозначность.
Не повторяй одну и ту же мысль дважды разными словами.

Вопрос:
{question}

Контекст:
{context}
""".strip()

    async def answer(
        self,
        game_title: str,
        question: str,
        model: str,
        status_callback: Callable[[str], Awaitable[None]] | None = None,
    ) -> RagAnswer:
        await self._notify_status(status_callback, "🔎 Рыскаю в священных писаниях и ищу нужные правила…")
        first_pass_chunks = await self.retriever.search(game_title=game_title, query=question, top_k=20)
        first_context = "\n\n".join(chunk.text for chunk in first_pass_chunks[:8])

        await self._notify_status(status_callback, "🧭 Сверяю формулировку вопроса с летописями игры…")
        scope_raw = await self.llm_client.generate(
            self._build_scope_prompt(game_title, question, first_context),
            model=model,
        )
        scope = self._parse_json(scope_raw) or {"is_relevant": True}
        if not scope.get("is_relevant", True):
            return RagAnswer(
                answer=self._out_of_scope_message(),
                chunks=[],
                used_deep_search=False,
            )

        await self._notify_status(status_callback, "🪶 Прикидываю, хватает ли найденных правил…")
        sufficiency_raw = await self.llm_client.generate(
            self._build_sufficiency_prompt(question, first_context),
            model=model,
        )
        sufficiency = self._parse_json(sufficiency_raw) or {
            "enough_context": True,
            "confidence": 1.0,
            "clarifying_queries": [],
        }

        candidate_groups = [first_pass_chunks]
        if not sufficiency.get("enough_context", True):
            await self._notify_status(status_callback, "🗺️ Уточняю запрос и собираю дополнительные фрагменты…")
            for clarifying_query in sufficiency.get("clarifying_queries", [])[:3]:
                extra_chunks = await self.retriever.search(
                    game_title=game_title,
                    query=clarifying_query,
                    top_k=12,
                )
                candidate_groups.append(extra_chunks)

        await self._notify_status(status_callback, "🎲 Перетасовываю найденные фрагменты и выбираю самые полезные…")
        final_candidates = self._merge_chunks(candidate_groups, limit=24)
        final_chunks = await self.reranker.rerank(question, final_candidates, top_k=5)
        final_context = "\n\n".join(chunk.text for chunk in final_chunks)
        final_check_raw = await self.llm_client.generate(
            self._build_sufficiency_prompt(question, final_context),
            model=model,
        )
        final_check = self._parse_json(final_check_raw) or {
            "enough_context": True,
            "confidence": 1.0,
            "clarifying_queries": [],
        }
        if not self._is_confident_enough(
            final_check.get("enough_context", True),
            float(final_check.get("confidence", 1.0)),
        ):
            return RagAnswer(
                answer=self._low_confidence_message(),
                chunks=final_chunks,
                used_deep_search=False,
            )
        await self._notify_status(status_callback, "✍️ Собираю короткий ответ по правилам…")
        answer = await self.llm_client.generate(self._build_answer_prompt(question, final_context), model=model)
        return RagAnswer(answer=answer, chunks=final_chunks, used_deep_search=False)
