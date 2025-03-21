from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.config import settings
from src.models.models import User
from src.database import get_db_session
from src.services.redis_client import RedisClient

# Inicializar RedisClient
redis_client = RedisClient()

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def create_access_token(data: dict, expires_delta: timedelta):
    """Genera un token de acceso con expiración."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def create_refresh_token(user_id: str):
    """Genera un refresh token y lo almacena en Redis."""
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = await create_access_token({"id": user_id}, refresh_token_expires)

    # Guardar en Redis con TTL en segundos
    await redis_client.set(
        f"refresh_token:{user_id}", refresh_token, ex=REFRESH_TOKEN_EXPIRE_DAYS * 86400
    )

    return refresh_token


async def create_tokens(user_id: str):
    """Genera un access token y un refresh token."""
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = await create_access_token({"id": user_id}, access_token_expires)
    refresh_token = await create_refresh_token(user_id)
    return access_token, refresh_token


async def get_current_user(
    token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_db_session)
):
    """Obtiene el usuario autenticado desde el access token."""
    credential_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("id")
        if user_id is None:
            raise credential_exception
    except JWTError:
        raise credential_exception

    result = await session.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if user is None:
        raise credential_exception

    return user


async def refresh_tokens(refresh_token: str):
    """Valida el refresh token y genera nuevos tokens."""
    credentials_exception = HTTPException(
        status_code=401,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("id")
        if not user_id:
            raise credentials_exception

        stored_token = await redis_client.get(f"refresh_token:{user_id}")

        if stored_token is None or stored_token != refresh_token:
            raise credentials_exception

        # Generar nuevos tokens
        new_access_token, new_refresh_token = await create_tokens(user_id)

        return new_access_token, new_refresh_token

    except JWTError:
        raise credentials_exception
