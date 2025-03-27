from sqlalchemy import MetaData, select, func, inspect, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm.exc import StaleDataError
from typing import Type, TypeVar, Optional, Tuple, List, Any, Union
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

    @classmethod
    async def read_all(
        cls: Type[T],
        session: AsyncSession,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        filters: Optional[List] = None,
    ) -> Tuple[List[T], int]:
        query = select(cls)
        count_query = select(func.count()).select_from(cls)

        if filters:
            query = query.where(*filters)
            count_query = count_query.where(*filters)

        if page is not None and page_size is not None:
            if page < 1:
                page = 1
            if page_size < 1:
                page_size = 10
            query = query.offset((page - 1) * page_size).limit(page_size)

        results = (await session.scalars(query)).all()
        total_count = await session.scalar(count_query)

        return results, total_count

    @classmethod
    async def read_by_id(cls: Type[T], session: AsyncSession, object_id: Any) -> T:
        pk_name = cls.get_pk_name()
        statement = select(cls).where(getattr(cls, pk_name) == object_id)
        entity = await session.scalar(statement)

        if entity is None:
            raise ValueError(f"{cls.__name__} con {pk_name}={object_id} no encontrado")
        return entity

    @classmethod
    async def create(cls: Type[T], session: AsyncSession, **kwargs) -> T:
        for key in kwargs:
            if not hasattr(cls, key):
                raise AttributeError(f"Atributo '{key}' no existe en {cls.__name__}")

        obj = cls(**kwargs)
        session.add(obj)
        await session.commit()
        return obj

    async def update(self, session: AsyncSession, **kwargs) -> None:
        self.__class__.validate_entity_data(kwargs)
        current_version = getattr(self, "version", None)

        pk_name = self.__class__.get_pk_name()
        pk_value = getattr(self, pk_name)

        # Verificación de concurrencia
        stmt = (
            select(self.__class__)
            .where(
                and_(
                    getattr(self.__class__, pk_name) == pk_value,
                    self.__class__.version == current_version,
                )
            )
            .with_for_update()
        )

        entity = await session.scalar(stmt)
        if not entity:
            raise StaleDataError("La entidad ha sido modificada por otro proceso")

        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

        if hasattr(self, "updated_at"):
            self.updated_at = datetime.now()

        await session.flush()

    @classmethod
    async def delete(cls: Type[T], session: AsyncSession, obj: Union[T, Any]) -> None:
        if not isinstance(obj, cls):
            obj = await cls.read_by_id(session, obj)

        await session.delete(obj)
        await session.flush()
