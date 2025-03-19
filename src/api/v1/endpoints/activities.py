from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from src.database import get_db_session
from src.models.models import Activity
from src.services.activity_services import ActivityService
from src.schemas.schemas import ActivityCreate, ActivityUpdate, ActivityResponse
from src.utils.auth.user_auth import get_current_user


router = APIRouter(prefix="/activities", tags=["Activities"])


@router.post("/", response_model=ActivityResponse)
async def create_activity(
    activity_data: ActivityCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """
    Permite a un usuario autenticado crear una actividad.
    Si no se especifica un tipo, se asigna el tipo "General".
    """
    try:
        activity = await ActivityService.create_activity(
            session,
            user_id=current_user.id,
            title=activity_data.title,
            description=activity_data.description,
            type_name=activity_data.type_name,
            type_color=activity_data.type_color,
        )
        return activity
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[ActivityResponse])
async def get_activities(
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
    page: int = 1,
    page_size: int = 10,
):
    """
    Obtiene todas las actividades del usuario autenticado.
    """
    activities, _ = await ActivityService.get_activities_by_user(
        session, user_id=current_user.id, page=page, page_size=page_size
    )
    return activities


@router.put("/{activity_id}", response_model=ActivityResponse)
async def update_activity(
    activity_id: str,
    activity_data: ActivityUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """
    Permite a un usuario autenticado actualizar una actividad si es el dueño.
    """
    try:
        updated_activity = await ActivityService.update_activity(
            session,
            activity_id=activity_id,
            user_id=current_user.id,
            title=activity_data.title,
            description=activity_data.description,
            type_name=activity_data.type_name,
            type_color=activity_data.type_color,
        )
        return updated_activity
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{activity_id}")
async def delete_activity(
    activity_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """
    Permite a un usuario autenticado eliminar una actividad si es el dueño.
    """
    try:
        await ActivityService.delete_activity(
            session, activity_id, user_id=current_user.id
        )
        return {"detail": "Actividad eliminada exitosamente"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
