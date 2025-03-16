from pydantic import EmailStr
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import List, Dict, Any
import bcrypt
import re
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
        DateTime, nullable=False, server_default=func.now()
    )
    is_staff: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relación 1:M con Activity
    activities: Mapped[List["Activity"]] = relationship(back_populates="user")

    def hash_password(self, password: str) -> str:
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

    # Relación 1:M con ActivityType
    types: Mapped[List["ActivityType"]] = relationship(back_populates="activity")


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

    # Relación M:1 con Activity
    activity_id: Mapped[str] = mapped_column(ForeignKey("activities.id"))
    activity: Mapped["Activity"] = relationship(back_populates="types")
