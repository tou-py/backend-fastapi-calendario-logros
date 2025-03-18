from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from typing import List
from src.models.models import ActivityType


class ActivityTypeService:
    @staticmethod
    async def create_activity_type(
        session: AsyncSession, name: str, color_asigned: str
    ) -> ActivityType:
        """
        Crea un nuevo tipo de actividad si no existe.
        """
        async with session.begin():
            result = await session.execute(select(ActivityType).filter_by(name=name))
            existing_type = result.scalars().first()

            if existing_type:
                raise ValueError("El tipo de actividad ya existe")

            new_type = await ActivityType.create(
                session, name=name, color_asigned=color_asigned
            )
            return new_type

    @staticmethod
    async def update_activity_type(
        session: AsyncSession, type_id: str, name: str, color_asigned: str
    ) -> ActivityType:
        """
        Actualiza un tipo de actividad existente.
        """
        async with session.begin():
            activity_type = await ActivityType.read_by_id(session, type_id)
            if not activity_type:
                raise ValueError("Tipo de actividad no encontrado")

            await activity_type.update(session, name=name, color_asigned=color_asigned)
            return activity_type

    @staticmethod
    async def delete_activity_type(session: AsyncSession, type_id: str):
        """
        Elimina un tipo de actividad por su ID.
        """
        try:
            async with session.begin():
                await ActivityType.delete(session, type_id)
        except Exception as ex:
            raise ValueError("Tipo de ctividad no encontrado")
