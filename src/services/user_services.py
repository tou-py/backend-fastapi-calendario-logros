from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError
from typing import Optional
from src.models.models import User
from src.schemas.schemas import UserCreate


class UserService:
    @staticmethod
    async def get_by_email(session: AsyncSession, email: str) -> Optional[User]:
        """Obtiene un usuario por email manejando errores de base de datos."""
        if not email:
            return None
        try:
            result = await session.execute(select(User).where(User.email == email))
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise ValueError(
                f"Error de base de datos al buscar por email: {str(e)}"
            ) from e

    @staticmethod
    async def get_by_username(session: AsyncSession, username: str) -> Optional[User]:
        """Obtiene un usuario por username manejando errores de base de datos."""
        if not username:
            return None
        try:
            result = await session.execute(
                select(User).where(User.username == username)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise ValueError(
                f"Error de base de datos al buscar por username: {str(e)}"
            ) from e

    @staticmethod
    async def create_user(session: AsyncSession, user_data: UserCreate) -> User:
        """Crea un nuevo usuario manejando errores de validación y base de datos."""
        try:
            # Validación básica de campos
            if not user_data.email:
                raise ValueError("El correo electrónico es obligatorio")
            if not user_data.username:
                raise ValueError("El nombre de usuario es obligatorio")

            # Verificación de existencia con manejo de errores
            try:
                existing_email = await UserService.get_by_email(
                    session, user_data.email
                )
                existing_username = await UserService.get_by_username(
                    session, user_data.username
                )
            except ValueError as e:
                raise ValueError(f"Error en verificación de datos: {str(e)}") from e

            if existing_email:
                raise ValueError("El correo electrónico ya está registrado")
            if existing_username:
                raise ValueError("El nombre de usuario ya está en uso")

            # Procesamiento seguro de contraseña
            user_dict = user_data.model_dump()
            try:
                password = user_dict.pop("password")
            except KeyError:
                raise ValueError("La contraseña es obligatoria")

            try:
                hashed_password = User().hash_password(password)
            except (TypeError, ValueError) as e:
                raise ValueError(f"Error al hashear la contraseña: {str(e)}") from e

            user_dict["hashed_password"] = hashed_password

            # Creación de usuario con manejo de transacciones
            try:
                user = await User.create(session, **user_dict)
                return user
            except IntegrityError as e:
                await session.rollback()
                raise ValueError(
                    "Conflicto de datos únicos: El email o username ya existen"
                ) from e
            except SQLAlchemyError as e:
                await session.rollback()
                raise ValueError(
                    f"Error de base de datos al crear usuario: {str(e)}"
                ) from e

        except StaleDataError as e:
            await session.rollback()
            raise ValueError("Conflicto de concurrencia al crear el usuario") from e
        except ValueError as e:
            await session.rollback()
            raise  # Re-lanza los ValueError ya formateados
        except Exception as e:
            await session.rollback()
            raise ValueError(f"Error inesperado: {str(e)}") from e
