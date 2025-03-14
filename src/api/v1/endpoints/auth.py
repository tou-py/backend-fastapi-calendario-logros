from fastapi import Depends, HTTPException, APIRouter
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from src.utils.auth.user_auth import (
    create_tokens,
    refresh_tokens,
)
from src.models.models import User
from src.database import get_db_session
from src.schemas.schemas import UserCreate
from src.schemas.schemas import UserCreate, UserResponse

router = APIRouter()


@router.post("/token")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_db_session),
):
    """Verifica las credenciales y devuelve access y refresh tokens."""
    user = session.query(User).filter(User.username == form_data.username).first()

    if not user or not user.verify_password(form_data.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token, refresh_token = create_tokens(user.username)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """Recibe un refresh token y devuelve nuevos access y refresh tokens."""
    new_access_token, new_refresh_token = refresh_tokens(refresh_token)
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@router.post("/register", response_model=UserResponse)
async def register_user(user: UserCreate, session: Session = Depends(get_db_session)):
    if not user:
        raise HTTPException(
            status_code=400, detail="An username and password should be provided"
        )
    try:
        new_user = User(
            username=user.username,
            email=user.email,
            hashed_password=User.hash_password(user.password),
        )
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return {"message": "User registered succesfully"}
    except Exception as ex:
        raise HTTPException(status_code=400, detail=f"str{ex}")
