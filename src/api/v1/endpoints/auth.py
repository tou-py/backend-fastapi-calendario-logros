from fastapi import Depends, HTTPException, APIRouter, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils.auth.user_auth import create_tokens, refresh_tokens
from src.models.models import User
from src.database import get_db_session
from src.schemas.schemas import UserCreate, UserResponse
from src.services.user_services import UserService
from typing import Dict, Any

router = APIRouter(prefix="/auth", tags=["User authentication"])


@router.post("/token")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Verifica las credenciales y devuelve access y refresh tokens.

    Args:
        form_data (OAuth2PasswordRequestForm): Datos de usuario y contraseña.
        session (AsyncSession): Sesión de base de datos.

    Returns:
        Dict: Tokens de acceso y refresco
    """
    result = await session.execute(
        select(User).filter(User.username == form_data.username)
    )
    user = result.scalars().first()

    if not user or not user.verify_password(form_data.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Crear tokens con user.id en lugar de username
    access_token, refresh_token = await create_tokens(user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh")
async def refresh_token(refresh_token: str) -> Dict[str, Any]:
    """
    Recibe un refresh token y devuelve nuevos access y refresh tokens.

    Args:
        refresh_token (str): Refresh token.

    Returns:
        Dict: Tokens de acceso y refresco actualizados.
    """
    new_access_token, new_refresh_token = await refresh_tokens(refresh_token)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register_user(
    user_data: UserCreate = Body(...), session: AsyncSession = Depends(get_db_session)
) -> UserResponse:
    """
    Registra usuarios en la base de datos.

    Args:
        user_data (UserCreate): Datos del usuario en esquema de pydantic
        session (AsyncSession): Session de la base de datos

    Returns:
        UserResponse: Datos del usuario
    """
    try:
        # Validación explícita de datos requeridos
        if not user_data.email:
            raise ValueError("El correo electrónico es obligatorio")

        user = await UserService.create_user(session, user_data)
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en el registro: {str(e)}",
        )
