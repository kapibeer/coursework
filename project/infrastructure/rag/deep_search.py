from collections.abc import Awaitable, Callable

from domain.entities.search import RagAnswer, SearchChunk
from infrastructure.rag.base_rag import BaseRAGService


class DeepSearchService(BaseRAGService):
    def __init__(self, retriever, reranker, llm_client, max_iterations: int = 3, min_confidence: float = 0.65) -> None:
        super().__init__(
            retriever=retriever,
            reranker=reranker,
            llm_client=llm_client,
            min_confidence=min_confidence,
        )
        self.max_iterations = max_iterations

    def _merge_with_entity_coverage(
        self,
        rule_groups: list[list[SearchChunk]],
        entity_groups: list[list[SearchChunk]],
        extra_groups: list[list[SearchChunk]] | None = None,
        limit: int = 18,
        entity_min_per_group: int = 1,
    ) -> list[SearchChunk]:
        extra_groups = extra_groups or []

        merged: list[SearchChunk] = []
        seen: set[str] = set()

        def add_chunk(chunk: SearchChunk) -> bool:
            key = self._normalize_text(chunk.text)
            if not chunk.text.strip() or key in seen:
                return False
            seen.add(key)
            merged.append(chunk)
            return True

        for group in entity_groups:
            added = 0
            for chunk in group:
                if add_chunk(chunk):
                    added += 1
                if added >= entity_min_per_group:
                    break
                if len(merged) >= limit:
                    return merged

        for groups in (rule_groups, entity_groups, extra_groups):
            for group in groups:
                for chunk in group:
                    add_chunk(chunk)
                    if len(merged) >= limit:
                        return merged

        return merged

    def _build_plan_prompt(self, game_title: str, question: str) -> str:
        return f"""
Ты помогаешь искать ответ в правилах настольной игры.

Игра: {game_title}
Вопрос: {question}

Сделай строгую декомпозицию вопроса.

Нужно определить:
- какое правило или спорный момент нужно проверить;
- 2-4 коротких подзапроса для поиска этого правила;
- ключевые игровые сущности;
- по одной короткой поисковой формулировке для каждой сущности, чтобы уточнить её роль в правилах.

Важно:
- не включай название игры в подзапросы;
- не подменяй исходный вопрос более общим сценарием;
- если вопрос зависит от порядка действий, явно учитывай это при формулировке подзапросов.

Ответь только JSON:
{{
  "rule": "...",
  "rule_queries": ["...", "..."],
  "entities": ["...", "..."],
  "entity_queries": [
    {{"entity": "...", "query": "..."}}
  ]
}}
""".strip()

    def _build_context_check_prompt(self, question: str, rule: str, context: str) -> str:
        return f"""
Ты проверяешь, достаточно ли контекста, чтобы корректно ответить на вопрос по правилам настольной игры.

Ответь только JSON:
{{
  "enough": true,
  "confidence": 0.0,
  "extra_queries": []
}}

или

{{
  "enough": false,
  "confidence": 0.0,
  "extra_queries": ["...", "..."]
}}

Если контекста недостаточно или уверенность низкая, сформулируй 1-3 коротких дополнительных поисковых запроса.

Проверяемое правило:
{rule}

Вопрос:
{question}

Контекст:
{context}
""".strip()

    def _build_answer_prompt(self, question: str, rule: str, entities: list[str], context: str) -> str:
        entities_text = ", ".join(entities)
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

Проверяемое правило:
{rule}

Ключевые сущности:
{entities_text}

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
        await self._notify_status(status_callback, "🧠 Разбираю спорный момент и раскладываю вопрос по полочкам…")
        plan_raw = await self.llm_client.generate(self._build_plan_prompt(game_title, question), model=model)
        plan = self._parse_json(plan_raw) or {
            "rule": question,
            "rule_queries": [question],
            "entities": [],
            "entity_queries": [],
        }

        rule_queries = plan.get("rule_queries", [])[:4] or [question]
        entity_queries = plan.get("entity_queries", [])[:5]

        rule_groups: list[list[SearchChunk]] = []
        await self._notify_status(status_callback, "📚 Ищу пункты правил, связанные с вопросом…")
        for query in rule_queries:
            chunks = await self.retriever.search(game_title=game_title, query=query, top_k=18)
            rule_groups.append(chunks[:6])

        entity_groups: list[list[SearchChunk]] = []
        await self._notify_status(status_callback, "🧩 Собираю сведения по ключевым сущностям и компонентам…")
        for item in entity_queries:
            query = (item.get("query", "") or "").strip()
            if not query:
                continue
            chunks = await self.retriever.search(game_title=game_title, query=query, top_k=8)
            entity_groups.append(chunks[:3])

        all_extra_groups: list[list[SearchChunk]] = []
        merged = self._merge_with_entity_coverage(
            rule_groups=rule_groups,
            entity_groups=entity_groups,
            extra_groups=all_extra_groups,
            limit=18,
            entity_min_per_group=1,
        )

        await self._notify_status(status_callback, "🧭 Проверяю, туда ли ведут найденные фрагменты правил…")
        scope_raw = await self.llm_client.generate(
            self._build_scope_prompt(
                game_title=game_title,
                question=question,
                context="\n\n".join(chunk.text for chunk in merged[:8]),
            ),
            model=model,
        )
        scope = self._parse_json(scope_raw) or {"is_relevant": True}
        if not scope.get("is_relevant", True):
            return RagAnswer(
                answer=self._out_of_scope_message(),
                chunks=[],
                used_deep_search=True,
            )

        for iteration in range(max(self.max_iterations - 1, 0)):
            await self._notify_status(
                status_callback,
                "🔍 Сопоставляю фрагменты и проверяю, не нужно ли копнуть глубже…"
                if iteration == 0
                else "🗺️ Делаю ещё один круг поиска по спорным местам…",
            )
            context_check_raw = await self.llm_client.generate(
                self._build_context_check_prompt(
                    question=question,
                    rule=plan.get("rule", question),
                    context="\n\n".join(chunk.text for chunk in merged),
                ),
                model=model,
            )
            context_check = self._parse_json(context_check_raw) or {
                "enough": True,
                "confidence": 1.0,
                "extra_queries": [],
            }
            if self._is_confident_enough(
                context_check.get("enough", True),
                float(context_check.get("confidence", 1.0)),
            ):
                break

            extra_groups: list[list[SearchChunk]] = []
            await self._notify_status(status_callback, "🕯️ Поднимаю дополнительные свитки и уточняю детали…")
            for extra_query in context_check.get("extra_queries", [])[:3]:
                chunks = await self.retriever.search(game_title=game_title, query=extra_query, top_k=12)
                extra_groups.append(chunks[:4])
            if not extra_groups:
                break
            all_extra_groups.extend(extra_groups)
            merged = self._merge_with_entity_coverage(
                rule_groups=rule_groups,
                entity_groups=entity_groups,
                extra_groups=all_extra_groups,
                limit=18,
                entity_min_per_group=1,
            )

        await self._notify_status(status_callback, "🎯 Отбираю самые сильные фрагменты перед финальным ответом…")
        final_chunks = await self.reranker.rerank(question, merged, top_k=8)
        final_context = "\n\n".join(chunk.text for chunk in final_chunks)
        final_check_raw = await self.llm_client.generate(
            self._build_context_check_prompt(
                question=question,
                rule=plan.get("rule", question),
                context=final_context,
            ),
            model=model,
        )
        final_check = self._parse_json(final_check_raw) or {
            "enough": True,
            "confidence": 1.0,
            "extra_queries": [],
        }
        if not self._is_confident_enough(
            final_check.get("enough", True),
            float(final_check.get("confidence", 1.0)),
        ):
            return RagAnswer(
                answer=self._low_confidence_message(),
                chunks=final_chunks,
                used_deep_search=True,
            )
        await self._notify_status(status_callback, "✍️ Собираю итоговый ответ по правилам…")
        answer = await self.llm_client.generate(
            self._build_answer_prompt(
                question=question,
                rule=plan.get("rule", question),
                entities=plan.get("entities", []),
                context=final_context,
            ),
            model=model,
        )
        return RagAnswer(answer=answer, chunks=final_chunks, used_deep_search=True)
