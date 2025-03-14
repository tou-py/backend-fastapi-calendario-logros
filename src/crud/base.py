from sqlalchemy import MetaData, select, func, inspect, and_
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm.exc import StaleDataError
from contextlib import asynccontextmanager
from typing import Type, TypeVar, Optional, Tuple, List, Any, Dict, Union
import asyncio
from datetime import datetime
from src.utils.validator import DataValidator

convention = {
    "ix": "id_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s",
    "pk": "pk_%(table_name)s",
}

T = TypeVar("T", bound="Base")

connection_semaphore = asyncio.Semaphore(20)  # Se limitan 20 conexiones concurrentes


class Base(DeclarativeBase, DataValidator):
    __abstract__ = True

    metadata = MetaData(naming_convention=convention)

    def __repr__(self):
        columns = ", ".join(
            [
                f"{key}={repr(value)}"
                for key, value in self.__dict__.items()
                if not key.startswith("_")
            ]
        )
        return f"<{self.__class__.__name__}({columns})>"

    @classmethod
    def get_pk_name(cls) -> str:
        return inspect(cls).primary_key[0].name

    @staticmethod
    @asynccontextmanager
    async def acquire_connection():
        acquired = False
        try:
            for attempt in range(5):
                acquired = await connection_semaphore.acquire()
                if acquired:
                    break
                await asyncio.sleep(0.5)

            if not acquired:
                raise Exception(
                    "No se pudo obtener una conexión después de varios intentos"
                )

            yield
        finally:
            if acquired:
                connection_semaphore.release()

    @classmethod
    @asynccontextmanager
    async def transaction(
        cls, session: AsyncSession, isolation_level=None, retry_count=3
    ):
        async with cls.acquire_connection():
            current_isolation = None
            connection = await session.connection()

            if isolation_level:
                current_isolation = await connection.get_isolation_level()
                await connection.execution_options(isolation_level=isolation_level)

            attempts = 0
            last_error = None

            while attempts < retry_count:
                attempts += 1
                try:
                    yield session
                    await session.commit()
                    break
                except StaleDataError as e:
                    await session.rollback()
                    last_error = e
                    if attempts < retry_count:
                        await asyncio.sleep(0.1 * attempts)
                    else:
                        raise Exception(
                            f"Error de concurrencia después de {retry_count} intentos: {str(e)}"
                        )
                except IntegrityError as e:
                    await session.rollback()
                    raise Exception(
                        f"Error de integridad en la base de datos: {str(e)}"
                    )
                except SQLAlchemyError as e:
                    await session.rollback()
                    raise Exception(f"Error de base de datos: {str(e)}")
                except Exception as e:
                    await session.rollback()
                    raise Exception(f"Error en la operación: {str(e)}")
                finally:
                    if current_isolation:
                        await connection.execution_options(
                            isolation_level=current_isolation
                        )

    @classmethod
    async def read_all(
        cls: Type[T],
        session: AsyncSession,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> Tuple[List[T], int]:
        try:
            query = select(cls)
            count_query = select(func.count()).select_from(cls)

            if page is not None and page_size is not None:
                if page < 1:
                    page = 1
                if page_size < 1:
                    page_size = 10

                query = query.offset((page - 1) * page_size).limit(page_size)

            async with cls.transaction(session, isolation_level="READ COMMITTED"):
                results = (await session.scalars(query)).all()
                total_count = await session.scalar(count_query)

            return results, total_count

        except Exception as ex:
            raise Exception(f"Error al leer las entidades: {str(ex)}")

    @classmethod
    async def read_by_id(cls: Type[T], session: AsyncSession, object_id: Any) -> T:
        try:
            pk_name = cls.get_pk_name()
            statement = select(cls).where(getattr(cls, pk_name) == object_id)

            entity = await session.scalar(statement)

            if entity is None:
                raise Exception(
                    f"No se encuentra {cls.__name__} con {pk_name}={object_id}"
                )
            return entity

        except Exception as ex:
            raise
        except SQLAlchemyError as ex:
            raise Exception(
                f"Error al leer {cls.__name__} con ID {object_id}: {str(ex)}"
            )

    @classmethod
    async def create(cls: Type[T], session: AsyncSession, **kwargs) -> T:
        try:
            cls.validate_entity_data(kwargs)

            async with cls.transaction(
                session, isolation_level="REPEATABLE READ", retry_count=3
            ):
                obj = cls(**kwargs)
                session.add(obj)
                await session.flush()
                return obj
        except Exception as e:
            raise Exception(f"Error al crear {cls.__name__}: {str(e)}")

    async def update(self, session: AsyncSession, **kwargs) -> None:
        try:
            self.__class__.validate_entity_data(kwargs)

            current_version = self.version

            async with self.__class__.transaction(
                session, isolation_level="REPEATABLE READ", retry_count=3
            ):
                pk_name = self.__class__.get_pk_name()
                pk_value = getattr(self, pk_name)

                verification = (
                    select(self.__class__)
                    .where(
                        and_(
                            getattr(self.__class__, pk_name) == pk_value,
                            self.__class__.version == current_version,
                        )
                    )
                    .with_for_update()
                )

                entity = await session.scalar(verification)
                if not entity:
                    raise Exception(f"La entidad ha sido modificada por otro proceso")

                for key, value in kwargs.items():
                    if hasattr(self, key):
                        setattr(self, key, value)

                self.updated_at = datetime.now()

                await session.flush()

        except StaleDataError as e:
            raise Exception(f"Conflicto de concurrencia al actualizar: {str(e)}")
        except Exception as e:
            raise Exception(f"Error al actualizar {self.__class__.__name__}: {str(e)}")

    @classmethod
    async def delete(cls: Type[T], session: AsyncSession, obj: Union[T, Any]) -> None:
        try:
            if not isinstance(obj, cls):
                obj = await cls.read_by_id(session, obj)

            pk_name = cls.get_pk_name()
            pk_value = getattr(obj, pk_name)

            async with cls.transaction(
                session, isolation_level="REPEATABLE READ", retry_count=3
            ):
                verification = (
                    select(cls)
                    .where(
                        and_(
                            getattr(cls, pk_name) == pk_value,
                        )
                    )
                    .with_for_update()
                )

                entity = await session.scalar(verification)
                if not entity:
                    raise Exception(f"La entidad ha sido modificada por otro proceso")

                await session.delete(obj)
                await session.flush()

        except StaleDataError as e:
            raise Exception(f"Conflicto de concurrencia al eliminar: {str(e)}")
        except Exception as e:
            raise Exception(f"Error al eliminar {cls.__name__}: {str(e)}")
