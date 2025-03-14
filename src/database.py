import contextlib
from typing import Any, AsyncIterator
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from src.config import settings


class DatabaseSessionManager:
    def __init__(self, session_url: str, engine_kwargs: dict[str, Any] = {}):
        self._engine: AsyncEngine = create_async_engine(session_url, **engine_kwargs)
        self._sessionmaker = sessionmaker(
            bind=self._engine, class_=AsyncSession, expire_on_commit=False
        )

    async def close(self):
        if self._engine is None:
            raise Exception("Database session manager is not initialized")
        await self._engine.dispose()  # Ahora es una función async

        self._engine = None
        self._sessionmaker = None

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncSession]:
        if self._engine is None:
            raise Exception("Database session manager is not initialized")

        async with self._engine.begin() as connection:
            try:
                yield connection
            except Exception as ex:
                await connection.rollback()
                raise ex

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._sessionmaker is None:
            raise Exception("Database session manager is not initialized")

        async with self._sessionmaker() as session:
            try:
                yield session
            except Exception as ex:
                await session.rollback()
                raise ex
            finally:
                await session.close()


# Inicialización del session manager con configuración asíncrona
sessionmanager = DatabaseSessionManager(
    settings.DATABASE_URL, {"echo": settings.ECHO_SQL}
)


# Dependencia para FastAPI: Obtener sesión async
async def get_db_session():
    async with sessionmanager.session() as session:
        yield session
