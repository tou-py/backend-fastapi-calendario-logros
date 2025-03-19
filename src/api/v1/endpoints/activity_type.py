from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db_session
from src.models.models import User
from src.services.activity_type_services import ActivityTypeService
from src.schemas.schemas import (
    ActivityTypeCreate,
    ActivityTypeUpdate,
    ActivityTypeResponse,
)
from src.utils.auth.user_auth import get_current_user

router = APIRouter(prefix="/activity-types", tags=["Activity Types"])


@router.post("/", response_model=ActivityTypeResponse)
async def create_activity_type_route(
    type_data: ActivityTypeCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Crea un nuevo tipo de actividad.
    """
    try:
        new_type = await ActivityTypeService.create_activity_type(
            db, type_data.name, type_data.color_asigned
        )
        await db.commit()
        return ActivityTypeResponse.model_validate(new_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{type_id}", response_model=ActivityTypeResponse)
async def update_activity_type_route(
    type_id: str,
    type_data: ActivityTypeUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Actualiza un tipo de actividad existente.
    """
    try:
        updated_type = await ActivityTypeService.update_activity_type(
            db, type_id, type_data.name, type_data.color_asigned
        )
        await db.commit()
        return ActivityTypeResponse.model_validate(updated_type)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{type_id}")
async def delete_activity_type_route(
    type_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Elimina un tipo de actividad.
    """
    await ActivityTypeService.delete_activity_type(db, type_id)
    await db.commit()
    return {"detail": "Tipo de actividad eliminado correctamente"}
