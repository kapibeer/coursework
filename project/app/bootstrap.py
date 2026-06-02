from aiogram import Bot, Dispatcher

from infrastructure.config.settings import Settings
from infrastructure.clients.polza import PolzaEmbeddingClient, PolzaLLMClient
from infrastructure.clients.telegram_session import build_bot
from infrastructure.db.postgres.base import Database
from infrastructure.db.postgres.favorite_repository import PostgresFavoriteGameRepository
from infrastructure.db.postgres.game_repository import PostgresGameRepository
from infrastructure.db.postgres.user_repository import PostgresUserRepository
from infrastructure.db.qdrant.chunk_repository import QdrantChunkRepository
from infrastructure.ingestion.ingestion_service import GameIngestionService
from infrastructure.ingestion.layout_segmenter import LayoutSegmenter
from infrastructure.ingestion.pdf_extractor import PdfTextExtractor
from infrastructure.ingestion.recursive_chunker import RecursiveChunker
from infrastructure.rag.deep_search import DeepSearchService
from infrastructure.rag.fast_search import FastSearchService
from infrastructure.rag.reranker import CrossEncoderReranker
from infrastructure.rag.retriever import Retriever
from presentation.telegram.handlers.admin import get_admin_router
from presentation.telegram.handlers.favorites import get_favorites_router
from presentation.telegram.handlers.menu import get_menu_router
from presentation.telegram.handlers.search import get_search_router
from usecases.favorites import FavoriteGamesUseCase
from usecases.games import GameCatalogUseCase
from usecases.onboarding import OnboardingUseCase
from usecases.search import SearchUseCase


class AppContainer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.database = Database(settings.postgres_dsn)
        self.bot = build_bot(settings)
        self.dispatcher = Dispatcher()

        self.user_repository = PostgresUserRepository(self.database)
        self.game_repository = PostgresGameRepository(self.database)
        self.favorite_repository = PostgresFavoriteGameRepository(self.database)
        self.chunk_repository = QdrantChunkRepository(settings)

        self.embedding_client = PolzaEmbeddingClient(settings)
        self.llm_client = PolzaLLMClient(settings)
        self.pdf_extractor = PdfTextExtractor()
        self.layout_segmenter = LayoutSegmenter()
        self.recursive_chunker = RecursiveChunker()
        self.reranker = CrossEncoderReranker(model_path="./models/BAAI-bge-reranker-v2-m3")
        self.retriever = Retriever(
            chunk_repository=self.chunk_repository,
            embedding_client=self.embedding_client,
            default_model=settings.default_retrieval_model,
            default_chunking=settings.default_chunking,
            default_chunk_size=settings.default_chunk_size,
        )
        self.ingestion_service = GameIngestionService(
            pdf_extractor=self.pdf_extractor,
            layout_segmenter=self.layout_segmenter,
            chunker=self.recursive_chunker,
            embedding_client=self.embedding_client,
            chunk_repository=self.chunk_repository,
            model_name=settings.default_retrieval_model,
            chunking=settings.default_chunking,
            chunk_size=settings.default_chunk_size,
        )
        self.fast_search = FastSearchService(
            retriever=self.retriever,
            reranker=self.reranker,
            llm_client=self.llm_client,
            retrieval_top_k=settings.fast_search_retrieval_top_k,
            context_top_k=settings.fast_search_context_top_k,
            clarifying_queries_limit=settings.fast_search_clarifying_queries_limit,
            extra_retrieval_top_k=settings.fast_search_extra_retrieval_top_k,
            rerank_top_k=settings.fast_search_rerank_top_k,
            min_confidence=settings.rag_min_confidence,
        )
        self.deep_search = DeepSearchService(
            retriever=self.retriever,
            reranker=self.reranker,
            llm_client=self.llm_client,
            max_iterations=settings.deep_search_max_iterations,
            rule_queries_limit=settings.deep_search_rule_queries_limit,
            entity_queries_limit=settings.deep_search_entity_queries_limit,
            rule_top_k=settings.deep_search_rule_top_k,
            entity_top_k=settings.deep_search_entity_top_k,
            scope_context_top_k=settings.deep_search_scope_context_top_k,
            extra_queries_limit=settings.deep_search_extra_queries_limit,
            extra_top_k=settings.deep_search_extra_top_k,
            rerank_top_k=settings.deep_search_rerank_top_k,
            min_confidence=settings.rag_min_confidence,
        )

        self.onboarding_use_case = OnboardingUseCase(self.user_repository)
        self.favorite_games_use_case = FavoriteGamesUseCase(self.favorite_repository, self.game_repository)
        self.game_catalog_use_case = GameCatalogUseCase(self.game_repository)
        self.search_use_case = SearchUseCase(self.fast_search, self.deep_search)

    def wire_routers(self) -> None:
        self.dispatcher.include_router(get_menu_router(self))
        self.dispatcher.include_router(get_favorites_router(self))
        self.dispatcher.include_router(get_search_router(self))
        self.dispatcher.include_router(get_admin_router(self))


def create_app(settings: Settings) -> tuple[Bot, Dispatcher, AppContainer]:
    container = AppContainer(settings)
    container.wire_routers()
    return container.bot, container.dispatcher, container
