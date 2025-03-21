import contextlib
from typing import Any, AsyncIterator
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from src.config import settings

# Construcción de la URL de la base de datos
DATABASE_URL = (
    f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@"
    f"{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
)


class DatabaseSessionManager:
    def __init__(self, session_url: str, engine_kwargs: dict[str, Any] = {}):
        self._engine: AsyncEngine = create_async_engine(session_url, **engine_kwargs)
        self._sessionmaker = sessionmaker(
            bind=self._engine, class_=AsyncSession, expire_on_commit=False
        )

    async def close(self):
        """Cierra el motor de la base de datos de forma segura."""
        if self._engine is None:
            raise Exception("Database session manager is not initialized")
        await self._engine.dispose()
        self._engine = None
        self._sessionmaker = None

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Proporciona una sesión de base de datos de forma segura."""
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


# Inicialización del session manager con configuración optimizada
sessionmanager = DatabaseSessionManager(
    DATABASE_URL, {"echo": settings.ECHO_SQL, "pool_size": 10, "max_overflow": 20}
)


# Dependencia para FastAPI: Obtener sesión async
async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Retorna una sesión de base de datos para FastAPI."""
    async with sessionmanager.session() as session:
        try:
            yield session
            if session.in_transaction():
                await session.commit()
        except Exception as ex:
            if session.in_transaction():
                await session.rollback()
            raise ex
