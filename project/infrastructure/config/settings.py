from functools import cached_property

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    bot_token: str = Field(alias="BOT_TOKEN")
    bot_proxy_url: str | None = Field(default=None, alias="BOT_PROXY_URL")
    polza_api_key: str = Field(alias="POLZA_API_KEY")
    polza_base_url: str = Field(default="https://api.polza.ai/api/v1", alias="POLZA_BASE_URL")
    postgres_host: str = Field(default="postgres", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="board_games_bot", alias="POSTGRES_DB")
    postgres_user: str = Field(default="board_games", alias="POSTGRES_USER")
    postgres_password: str = Field(default="board_games", alias="POSTGRES_PASSWORD")
    qdrant_url: str = Field(default="http://qdrant:6333", alias="QDRANT_URL")
    qdrant_api_key: str | None = Field(default=None, alias="QDRANT_API_KEY")
    admin_telegram_ids_raw: str = Field(default="", alias="ADMIN_TELEGRAM_IDS")
    bot_log_level: str = Field(default="INFO", alias="BOT_LOG_LEVEL")
    default_retrieval_model: str = Field(default="google/gemini-embedding-001", alias="DEFAULT_RETRIEVAL_MODEL")
    default_generation_model: str = Field(
        default="qwen/qwen3-next-80b-a3b-instruct",
        alias="DEFAULT_GENERATION_MODEL",
    )
    default_chunking: str = Field(default="recursive", alias="DEFAULT_CHUNKING")
    default_chunk_size: int = Field(default=512, alias="DEFAULT_CHUNK_SIZE")
    fast_search_retrieval_top_k: int = Field(default=20, alias="FAST_SEARCH_RETRIEVAL_TOP_K")
    fast_search_rerank_top_k: int = Field(default=5, alias="FAST_SEARCH_RERANK_TOP_K")
    deep_search_max_iterations: int = Field(default=3, alias="DEEP_SEARCH_MAX_ITERATIONS")
    rag_min_confidence: float = Field(default=0.25, alias="RAG_MIN_CONFIDENCE")

    @cached_property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @cached_property
    def admin_telegram_ids(self) -> set[int]:
        values = [value.strip() for value in self.admin_telegram_ids_raw.split(",") if value.strip()]
        return {int(value) for value in values}
