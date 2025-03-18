from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from typing import List
from src.database import get_db_session
from src.models.models import Activity, ActivityType, User
from src.services.activity_services import ActivityService
from src.schemas.schemas import ActivityCreate, ActivityResponse
from src.utils.auth.user_auth import get_current_user

router = APIRouter(prefix="activities", tags=["User Activities"])


@router.post("/", response_model=ActivityResponse)
async def create_activity(
    activity_data: ActivityCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Endpoint para que un usuario autenticado cree una actividad.
    Si no especifica un tipo, se asignará el tipo "General".
    """
    try:
        new_activity = await ActivityService.create_activity(
            session=db,
            user_id=current_user.id,
            title=activity_data.title,
            description=activity_data.description,
            type_name=activity_data.type_name,
            type_color=activity_data.type_color,
        )

        await db.commit()
        return new_activity

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IntegrityError:
        raise HTTPException(
            status_code=400, detail="Error de integridad en la base de datos"
        )


@router.get("/user-activities/", response_model=List[ActivityResponse])
async def get_user_activities(
    page: int = 1,
    page_size: int = 10,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Endpoint para obtener todas las actividades del usuario autenticado, paginadas.
    """
    activities, total = await ActivityService.get_activities_by_user(
        db, current_user.id, page, page_size
    )
    return activities
