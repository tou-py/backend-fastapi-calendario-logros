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
            # valida campos obligatorios
            required_fields = {"username", "email", "password"}
            user_dict = user_data.model_dump()

            missing_fields = [
                field for field in required_fields if not user_dict.get(field)
            ]

            if missing_fields:
                raise ValueError(
                    f"Faltan los siguientes campos obligatorios: {',' .join(missing_fields)}"
                )

            # verificar si el usuario ya existe
            if await UserService.get_by_email(session, user_data.email):
                raise ValueError("El correo ya esta registrado")
            if await UserService.get_by_username(session, user_data.username):
                raise ValueError("El nombre de usuario no se encuentra disponible")

            password = user_dict.pop("password", None)
            if not password:
                raise ValueError("La contrasnia es obligatoria")

            user_dict["hashed_password"] = User.hash_password(password)

            # crear el usuario
            try:
                return await User.create(session, **user_dict)
            except IntegrityError:
                await session.rollback()
                raise ValueError(
                    "Conflicto de datos unicos, email o username ya en uso"
                )
            except SQLAlchemyError as ex:
                await session.rollback()
                raise ValueError(
                    f"Error en base de datos al crear usuario: {str(ex)}"
                ) from ex

        except (StaleDataError, ValueError) as ex:
            await session.rollback()
            raise ex
        except Exception as ex:
            await session.rollback()
            raise ValueError(f"Error inesperado: {str(ex)}") from ex
