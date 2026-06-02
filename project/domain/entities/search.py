from dataclasses import dataclass, field


@dataclass(slots=True)
class SearchChunk:
    text: str
    score: float | None = None
    payload: dict | None = None


@dataclass(slots=True)
class RagAnswer:
    answer: str
    chunks: list[SearchChunk] = field(default_factory=list)
    used_deep_search: bool = False
