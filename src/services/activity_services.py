from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from src.models.models import Activity, User, ActivityType


class ActivityService:
    @staticmethod
    async def create_activity(
        session: AsyncSession,
        user_id: str,
        title: str,
        description: Optional[str] = None,
        type_name: Optional[str] = None,
        type_color: Optional[str] = None,
    ) -> Activity:
        """
        Crea una actividad para un usuario, asignándole un tipo existente o creando uno nuevo si es necesario.
        Si no se especifica un tipo, se asigna el tipo por defecto "General".
        """
        async with session.begin():  # Manejo automático de transacciones
            # Verificar si el usuario existe
            user = await User.read_by_id(session, user_id)
            if not user:
                raise ValueError("El usuario no existe")

            # Buscar o crear el tipo de actividad
            if type_name:
                result = await session.execute(
                    select(ActivityType).filter_by(name=type_name)
                )
                activity_type = result.scalars().first()

                if not activity_type:
                    # Si el tipo no existe, crearlo
                    activity_type = ActivityType(
                        name=type_name, color_asigned=type_color or "#FFFFFF"
                    )
                    session.add(activity_type)
                    await session.flush()  # Para obtener el ID generado

            else:
                # Si no se proporciona un tipo, buscar o crear "General"
                result = await session.execute(
                    select(ActivityType).filter_by(name="General")
                )
                activity_type = result.scalars().first()

                if not activity_type:
                    activity_type = ActivityType(
                        name="General", color_asigned="#F6F6F6"
                    )
                    session.add(activity_type)
                    await session.flush()

            # Crear la actividad
            activity = await Activity.create(
                session, user_id=user_id, title=title, description=description
            )

            # Asignar el tipo de actividad
            activity.types.append(activity_type)
            await session.flush()
            return activity

    @staticmethod
    async def get_activities_by_user(
        session: AsyncSession, user_id: str, page: int = 1, page_size: int = 10
    ):
        """
        Obtiene todas las actividades de un usuario paginadas.
        """
        filters = [Activity.user_id == user_id]
        activities, total = await Activity.read_all(
            session, page=page, page_size=page_size, filters=filters
        )
        return activities, total

    @staticmethod
    async def update_activity(
        session: AsyncSession,
        activity_id: str,
        user_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        type_name: Optional[str] = None,
        type_color: Optional[str] = None,
    ) -> Activity:
        """
        Actualiza una actividad solo si pertenece al usuario autenticado.
        También permite cambiar su tipo de actividad.
        """
        async with session.begin():
            # Buscar la actividad
            activity = await Activity.read_by_id(session, activity_id)
            if not activity:
                raise ValueError("Actividad no encontrada")

            # Verificar si el usuario es dueño de la actividad
            if activity.user_id != user_id:
                raise ValueError("No tienes permiso para modificar esta actividad")

            # Actualizar los datos de la actividad
            update_data = {}
            if title:
                update_data["title"] = title
            if description:
                update_data["description"] = description

            if update_data:
                await activity.update(session, **update_data)

            # Cambiar tipo de actividad si se proporciona un nuevo tipo
            if type_name:
                result = await session.execute(
                    select(ActivityType).filter_by(name=type_name)
                )
                activity_type = result.scalars().first()

                if not activity_type:
                    activity_type = ActivityType(
                        name=type_name, color_asigned=type_color or "#FFFFFF"
                    )
                    session.add(activity_type)
                    await session.flush()

                activity.types.clear()  # Eliminar tipos anteriores
                activity.types.append(activity_type)

            await session.flush()
            return activity

    @staticmethod
    async def delete_activity(session: AsyncSession, activity_id: str, user_id: str):
        """
        Elimina una actividad solo si pertenece al usuario autenticado.
        """
        async with session.begin():
            # Buscar la actividad
            activity = await Activity.read_by_id(session, activity_id)
            if not activity:
                raise ValueError("Actividad no encontrada")

            # Verificar si el usuario es dueño de la actividad
            if activity.user_id != user_id:
                raise ValueError("No tienes permiso para eliminar esta actividad")

            # Eliminar la actividad
            await Activity.delete(session, activity)
            await session.flush()
