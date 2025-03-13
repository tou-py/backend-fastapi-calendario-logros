from sqlalchemy import MetaData, select, func, inspect, and_
from sqlalchemy.orm import DeclarativeBase, Session, Mapped, mapped_column
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm.exc import StaleDataError
from contextlib import contextmanager
from typing import Type, TypeVar, Optional, Tuple, List, Any, Dict, Union
import threading
import time
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

connection_semaphore = threading.Semaphore(20)  # Se limitan 20 conexiones concurrentes


class Base(DeclarativeBase, DataValidator):
    __abstract__ = True

    metadata = MetaData(naming_convention=convention)

    def __repr__(self):
        """
        Representacion legible de la instancia
        """
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
        """
        obtiene el nombre dde la clave primaria de la entidad
        """
        return inspect(cls).primary_key[0].name

    @staticmethod
    @contextmanager
    def acquire_connection():
        """
        Administrador de contexto para limitar el número de conexiones concurrentes.
        Usa un semáforo para controlar el número máximo de conexiones.
        """
        acquired = False
        try:
            # Intentar adquirir el semáforo con un tiempo de espera
            for attempt in range(5):  # 5 intentos
                acquired = connection_semaphore.acquire(blocking=False)
                if acquired:
                    break
                # Esperar antes de reintentar
                time.sleep(0.5)

            if not acquired:
                raise Exception(
                    "No se pudo obtener una conexión después de varios intentos"
                )

            yield
        finally:
            if acquired:
                connection_semaphore.release()

    @classmethod
    @contextmanager
    def transaction(cls, session: Session, isolation_level=None, retry_count=3):
        """
        Administrador de contexto para manejar transacciones con soporte para niveles de aislamiento
        y reintentos.

        Args:
            session: Sesión de SQLAlchemy
            isolation_level: Nivel de aislamiento de la transacción
            retry_count: Número de reintentos para transacciones fallidas

        Yields:
            La sesión proporcionada

        Raises:
            Exception: Si ocurre un error durante la transacción
        """
        with cls.acquire_connection():
            # Guardar el nivel de aislamiento actual si se especificó uno nuevo
            current_isolation = None
            connection = session.connection()

            if isolation_level:
                current_isolation = connection.get_isolation_level()
                connection.execution_options(isolation_level=isolation_level)

            attempts = 0
            last_error = None

            while attempts < retry_count:
                attempts += 1
                try:
                    yield session
                    session.commit()
                    break
                except StaleDataError as e:
                    session.rollback()
                    last_error = e
                    if attempts < retry_count:
                        time.sleep(0.1 * attempts)  # Backoff exponencial
                    else:
                        raise Exception(
                            f"Error de concurrencia después de {retry_count} intentos: {str(e)}"
                        )
                except IntegrityError as e:
                    session.rollback()
                    raise Exception(
                        f"Error de integridad en la base de datos: {str(e)}"
                    )
                except SQLAlchemyError as e:
                    session.rollback()
                    raise Exception(f"Error de base de datos: {str(e)}")
                except Exception as e:
                    session.rollback()
                    raise Exception(f"Error en la operación: {str(e)}")
                finally:
                    # Restaurar el nivel de aislamiento si se cambió
                    if current_isolation:
                        connection.execution_options(isolation_level=current_isolation)

    @classmethod
    def read_all(
        cls: Type[T],
        session: Session,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> Tuple[List[T], int]:
        """
        Lee todas las entidades, con paginacion

        Args:
            session: Session de SQLAlchemy
            page: numero de pagina
            page_size: tamanio de la pagina

        Returns:
            Tupla con la lista de entidades y el total de registros
        """

        try:
            query = select(cls)
            count_query = select(func.count()).select_from(cls)

            # Aplicar paginacion si se especifica
            if page is not None and page_size is not None:
                if page < 1:
                    page = 1
                if page_size < 1:
                    page_size = 10

                query = query.offset((page - 1) * page_size).limit(page_size)

            with cls.transaction(session, isolation_level="READ COMMITED"):
                results = session.scalars(query).all()
                total_count = session.scalar(count_query)

            return results, total_count

        except Exception as ex:
            raise Exception(f"Error al leer las entidades: {str(ex)}")

    @classmethod
    def read_by_id(cls: Type[T], session: Session, object_id: Any) -> T:
        """
        Lee una entidad por su ID.

        Args:
            session: Sesión de SQLAlchemy
            object_id: ID del objeto a buscar

        Returns:
            La entidad encontrada

        Raises:
            EntityNotFoundException: Si no se encuentra la entidad
        """
        try:
            pk_name = cls.get_pk_name()
            statement = select(cls).where(getattr(cls, pk_name) == object_id)

            entity = session.scalar(statement)

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
    def create(cls: Type[T], session: Session, **kwargs) -> T:
        """
        Crea una nueva instancia de la entidad.

        Args:
            session: Sesión de SQLAlchemy
            **kwargs: Atributos para la nueva entidad

        Returns:
            La nueva entidad creada

        Raises:
            ValidationError: Si los datos no son válidos
            CRUDException: Si ocurre un error durante la creación
        """
        try:
            # Validar datos de entrada
            cls.validate_entity_data(kwargs)

            # Crear y persistir entidad
            with cls.transaction(
                session, isolation_level="REPEATABLE READ", retry_count=3
            ):
                obj = cls(**kwargs)
                session.add(obj)
                session.flush()
                return obj
        except Exception as e:
            raise Exception(f"Error al crear {cls.__name__}: {str(e)}")

    def update(self, session: Session, **kwargs) -> None:
        """
        Actualiza los atributos de la entidad usando control de versiones optimista.

        Args:
            session: Sesión de SQLAlchemy
            **kwargs: Nuevos valores para los atributos

        Raises:
            ValidationError: Si los datos no son válidos
            ConcurrencyError: Si hay un conflicto de concurrencia
            CRUDException: Si ocurre un error durante la actualización
        """
        try:
            # Validar datos de entrada
            self.__class__.validate_entity_data(kwargs)

            # Guardar versión actual y la incrementamos
            current_version = self.version

            # Actualizar atributos
            with self.__class__.transaction(
                session, isolation_level="REPEATABLE READ", retry_count=3
            ):
                # Verificar que la versión no ha cambiado
                pk_name = self.__class__.get_pk_name()
                pk_value = getattr(self, pk_name)

                # Consulta que verifica la versión
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

                entity = session.scalar(verification)
                if not entity:
                    raise Exception(f"La entidad ha sido modificada por otro proceso")

                # Actualizar atributos
                for key, value in kwargs.items():
                    if hasattr(self, key):
                        setattr(self, key, value)

                self.updated_at = datetime.now()

                session.flush()

        except StaleDataError as e:
            raise Exception(f"Conflicto de concurrencia al actualizar: {str(e)}")
        except Exception as e:
            raise Exception(f"Error al actualizar {self.__class__.__name__}: {str(e)}")

    @classmethod
    def delete(cls: Type[T], session: Session, obj: Union[T, Any]) -> None:
        """
        Elimina una entidad.

        Args:
            session: Sesión de SQLAlchemy
            obj: Entidad a eliminar o ID de la entidad

        Raises:
            EntityNotFoundException: Si no se encuentra la entidad
            ConcurrencyError: Si hay un conflicto de concurrencia
            CRUDException: Si ocurre un error durante la eliminación
        """
        try:
            # Si se pasó un ID en lugar de un objeto, obtener el objeto primero
            if not isinstance(obj, cls):
                obj = cls.read_by_id(session, obj, lock_mode="FOR UPDATE")

            pk_name = cls.get_pk_name()
            pk_value = getattr(obj, pk_name)

            # Eliminar entidad
            with cls.transaction(
                session, isolation_level="REPEATABLE READ", retry_count=3
            ):
                # Verificar que la versión no ha cambiado
                verification = (
                    select(cls)
                    .where(
                        and_(
                            getattr(cls, pk_name) == pk_value,
                        )
                    )
                    .with_for_update()
                )

                entity = session.scalar(verification)
                if not entity:
                    raise Exception(f"La entidad ha sido modificada por otro proceso")

                session.delete(obj)
                session.flush()

        except StaleDataError as e:
            raise Exception(f"Conflicto de concurrencia al eliminar: {str(e)}")
        except Exception as e:
            raise Exception(f"Error al eliminar {cls.__name__}: {str(e)}")
