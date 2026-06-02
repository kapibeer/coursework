from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from infrastructure.db.postgres.models import Base


class Database:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def connect(self) -> None:
        self._engine = create_async_engine(self._dsn, future=True, echo=False)
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            raise RuntimeError("Database is not connected")
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            raise RuntimeError("Database is not connected")
        return self._session_factory

    async def dispose(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
