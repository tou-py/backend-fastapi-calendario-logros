from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db_session
from src.utils.auth.user_auth import get_current_user
from src.models.models import Activity, User
from src.schemas.schemas import ActivityResponse
from typing import List

router = APIRouter()


@router.get("/activities", response_model=List[ActivityResponse])
async def get_user_activities(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    page: int = 1,
    page_size: int = 10,
):
    """
    Obtiene todas las actividades del usuario autenticado.
    - `current_user` → Se obtiene a partir del token de autenticación.
    - `session` → Sesión de base de datos asíncrona.
    - `page` y `page_size` → Para paginación.
    """
    try:
        activities, total_count = await Activity.read_all(
            session=session,
            page=page,
            page_size=page_size,
            filters=[Activity.user_id == current_user.id],
        )

        return activities, total_count
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener actividades: {str(e)}"
        )
