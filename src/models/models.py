from pydantic import EmailStr
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
from typing import List
import bcrypt
import uuid
from src.crud.base import Base

email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        primary_key=True,
        unique=True,
        nullable=False,
        index=True,
        default=lambda: str(uuid.uuid4()),
    )
    username: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    email: Mapped[EmailStr] = mapped_column(String(64), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(60), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )
    last_login: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    is_staff: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relación 1:M con Activity
    activities: Mapped[List["Activity"]] = relationship(back_populates="user")

    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def verify_password(self, password: str) -> bool:
        return bcrypt.checkpw(
            password.encode("utf-8"), self.hashed_password.encode("utf-8")
        )

    def validate_user_data(self, **kwargs):
        if "email" in kwargs and hasattr(self, "email"):
            import re

            email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
            if not re.match(email_regex, kwargs["email"]):
                raise ValueError("El correo proporcionado no es válido")


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[str] = mapped_column(
        primary_key=True,
        unique=True,
        nullable=False,
        index=True,
        default=lambda: str(uuid.uuid4()),
    )
    title: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(String(256), nullable=True)
    activity_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    # Relación 1:M con User (Cada actividad pertenece a un usuario)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship(back_populates="activities")

    # Relación M:1 con ActivityType (Cada actividad tiene un solo tipo)
    type_id: Mapped[str] = mapped_column(ForeignKey("activity_types.id"))
    type: Mapped["ActivityType"] = relationship(back_populates="activities")

    async def set_default_type(self, session: AsyncSession):
        """Asegura que la actividad tenga un tipo si no le es proveido uno"""
        if not self.types:
            result = await session.execute(
                select(ActivityType).filter_by(name="General")
            )
            default_type = result.scalars().first()
            if not default_type:
                default_type = ActivityType(name="General", color_asigned="#F6F6F6")
                session.add(default_type)
                await session.commit()
            self.types.append(default_type)


class ActivityType(Base):
    __tablename__ = "activity_types"

    id: Mapped[str] = mapped_column(
        primary_key=True,
        unique=True,
        nullable=False,
        index=True,
        default=lambda: str(uuid.uuid4()),
    )
    name: Mapped[str] = mapped_column(String(16), nullable=False)
    color_asigned: Mapped[str] = mapped_column(String(7), nullable=False)

    # Relación 1:M con Activity (Un tipo puede pertenecer a muchas actividades)
    activities: Mapped[List["Activity"]] = relationship(back_populates="type")
