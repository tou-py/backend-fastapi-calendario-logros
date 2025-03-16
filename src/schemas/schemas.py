from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from datetime import datetime
from typing import List, Optional
import re


# Modelo base con atributos comunes
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    email: EmailStr = Field(...)
    is_active: bool = True
    is_staff: bool = False

    @field_validator("username")
    def username_alphanumeric(cls, v):
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError(
                "El nombre de usuario solo puede contener letras, números y guiones bajos"
            )
        return v


# Modelo para crear usuario (se requiere la contraseña en texto plano)
class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=64)


# Modelo para actualizar usuario (opcional)
class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=20)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6, max_length=64)
    is_active: Optional[bool] = None
    is_staff: Optional[bool] = None


# Modelo de respuesta (excluye la contraseña)
class UserResponse(UserBase):
    id: str
    last_login: datetime

    model_config = ConfigDict(from_attributes=True)


# Modelo interno que incluye la contraseña hasheada
class UserDB(UserResponse):
    hashed_password: str


class ActivityBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=32)
    description: Optional[str] = Field(None, max_length=256)


class ActivityCreate(ActivityBase):
    activity_date: Optional[datetime] = None
    user_id: str


class ActivityUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=32)
    description: Optional[str] = Field(None, max_length=256)
    activity_date: Optional[datetime] = None


class ActivityResponse(ActivityBase):
    id: str
    activity_date: datetime
    user_id: str
    types: List["ActivityTypeResponse"] = []

    model_config = ConfigDict(from_attributes=True)


class ActivityTypeBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=16)
    color_asigned: str = Field(
        ..., min_length=7, max_length=7, pattern="^#[0-9A-Fa-f]{6}$"
    )


class ActivityTypeCreate(ActivityTypeBase):
    activity_id: str


class ActivityTypeResponse(ActivityTypeBase):
    id: str
    activity_id: str

    model_config = {"from_attributes": True}
