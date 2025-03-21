from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from src.database import get_db_session
from src.models.models import User
from src.services.activity_services import ActivityService
from src.schemas.schemas import ActivityCreate, ActivityUpdate, ActivityResponse
from src.utils.auth.user_auth import get_current_user


router = APIRouter(prefix="/activities", tags=["Activities"])


@router.post("/", response_model=ActivityResponse)
async def create_activity(
    activity_data: ActivityCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> ActivityResponse:
    """
    Permite a un usuario autenticado crear una actividad.
    Si no se especifica un tipo, se asigna el tipo "General".

    Args:
        activity_data (ActivityCreate): Datos de la actividad.
        session (AsyncSession): Sesión de base de datos.
        current_user (User): Usuario autenticado.

    Returns:
        ActivityResponse: Actividad creada
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
        return ActivityResponse.model_validate(activity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[ActivityResponse])
async def get_activities(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    page: int = 1,
    page_size: int = 10,
) -> List[ActivityResponse]:
    """
    Obtiene todas las actividades del usuario autenticado.

    Args:
        session (AsyncSession): Session de la base de datos
        current_user (User): Usuario previamente autenticado
        page (int): Numero de pagina

    Returns:
        List[ActivityResponse]: Lista de actividades del usuario
    """
    activities, _ = await ActivityService.get_activities_by_user(
        session, user_id=current_user.id, page=page, page_size=page_size
    )
    return List[ActivityResponse].model_validate(activities)


@router.put("/{activity_id}", response_model=ActivityResponse)
async def update_activity(
    activity_id: str,
    activity_data: ActivityUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> ActivityResponse:
    """
    Permite a un usuario autenticado actualizar una actividad si es el dueño.

    args:
        activity_id (str): ID de la actividad
        activity_data (ActivitUpdate): Datos de la actividad
        session (AsyncSession): Sesion de la base de datos
        current_user (User): Usuario autenticado

    Returns:
        ActivityResponse: Actividad actualizada
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
        return ActivityResponse.model_validate(updated_activity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{activity_id}")
async def delete_activity(
    activity_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Permite a un usuario autenticado eliminar una actividad si es el dueño.

    Args:
        activity_id (str): ID de la actividad
        session (AsyncSession): Session de la base de datos
        current_user (User): Usuario autenticado

    Returns:
        Dict: Mensaje de confirmacion de eliminacion
    """
    try:
        await ActivityService.delete_activity(
            session, activity_id, user_id=current_user.id
        )
        return {"detail": "Actividad eliminada exitosamente"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
