import contextlib
from typing import Any, Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from . import settings


class DatabaseSessionManager:
    def __init__(self, session: str, engine_kwargs: dict[str, Any] = {}):
        self._engine = create_engine(session, **engine_kwargs)
        self._sessionmaker = sessionmaker(
            autocommit=False, bind=self._engine, expire_on_commit=False
        )

    def close(self):
        if self._engine is None:
            raise Exception("Database session manager is not initialized")
        self._engine.dispose()

        self._engine = None
        self._sessionmaker = None

    @contextlib.contextmanager
    def connect(self) -> Iterator[Session]:
        if self._engine is None:
            raise Exception("Database session manager is not initialized")

        with self._engine.begin() as connection:
            try:
                yield connection
            except Exception as ex:
                connection.rollback()
                raise ex

    @contextlib.contextmanager
    def session(self) -> Iterator[Session]:
        if self._sessionmaker is None:
            raise Exception("Database session manager is not initialized")

        session = self._sessionmaker()
        try:
            yield session
        except Exception as ex:
            session.rollback()
            raise ex
        finally:
            session.close()


sessionmanager = DatabaseSessionManager(
    settings.DATABASE_URL, {"echo": settings.ECHO_SQL}
)


def get_db_session():
    with sessionmanager.session() as session:
        yield session
