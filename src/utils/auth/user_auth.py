from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from src.config import settings
from src.models.models import User
from src.database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Simulación de almacenamiento de refresh tokens (debería estar en la BD)
refresh_tokens_db = {}


def create_access_token(data: dict, expires_delta: timedelta):
    """Genera un token de acceso con expiración."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str, username: str):
    """Genera un refresh token y lo almacena."""
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = create_access_token(
        {"sub": username, "id": user_id}, refresh_token_expires
    )

    # Guardar en la base de datos simulada
    refresh_tokens_db[username] = refresh_token

    return refresh_token


def create_tokens(user_id: str, username: str):
    """Genera un access token y un refresh token con id y username."""
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        {"sub": username, "id": user_id}, access_token_expires
    )
    refresh_token = create_refresh_token(user_id, username)

    return access_token, refresh_token


def get_current_user(
    token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_db_session)
):
    credential_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: str = payload.get("id")  # Obtener el ID

        if username is None or user_id is None:
            raise credential_exception
    except JWTError:
        raise credential_exception

    user = (
        session.query(User)
        .filter(User.id == user_id, User.username == username)
        .first()
    )
    if user is None:
        raise credential_exception

    return user  # Retorna el usuario autenticado


def refresh_tokens(refresh_token: str):
    """Valida el refresh token y genera nuevos access y refresh tokens."""
    credentials_exception = HTTPException(
        status_code=401,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

        # Verificar que el refresh token es válido
        stored_token = refresh_tokens_db.get(username)
        if stored_token != refresh_token:
            raise credentials_exception

        # Generar nuevos tokens
        new_access_token, new_refresh_token = create_tokens(username)

        return new_access_token, new_refresh_token
    except JWTError:
        raise credentials_exception
