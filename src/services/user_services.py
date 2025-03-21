from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError
from typing import Optional
from datetime import datetime, timezone
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
            # Extraer y validar password antes de hacer cualquier cambio
            password = user_data.password
            if not password:
                raise ValueError("La contraseña es obligatoria")

            # Convertir el objeto Pydantic en diccionario
            user_dict = user_data.model_dump(exclude={"password"})

            # Asignar valores predeterminados explícitos
            user_dict.setdefault("is_active", True)
            user_dict.setdefault("is_staff", False)
            user_dict["last_login"] = datetime.now(timezone.utc).replace(tzinfo=None)

            # Verificar si el usuario ya existe
            if await UserService.get_by_email(session, user_data.email):
                raise ValueError("El correo ya está registrado")
            if await UserService.get_by_username(session, user_data.username):
                raise ValueError("El nombre de usuario no está disponible")

            # Hashear la contraseña
            user_dict["hashed_password"] = User.hash_password(password)

            # Intentar crear el usuario en la base de datos
            try:
                return await User.create(session, **user_dict)
            except IntegrityError as ex:
                print(f"ACA ESTA EL ERROR: {str(ex)}")
                await session.rollback()
                raise ValueError(
                    "Conflicto de datos únicos: el email o username ya están en uso"
                )
            except SQLAlchemyError as ex:
                print(f"ACA ESTA EL ERROR: {str(ex)}")
                await session.rollback()
                raise ValueError(
                    f"Error en base de datos al crear usuario: {str(ex)}"
                ) from ex

        except (StaleDataError, ValueError) as ex:
            print(f"ACA ESTA EL ERROR: {str(ex)}")
            await session.rollback()
            raise ex
        except Exception as ex:
            print(f"ACA ESTA EL ERROR: {str(ex)}")
            await session.rollback()
            raise ValueError(f"Error inesperado: {str(ex)}") from ex
