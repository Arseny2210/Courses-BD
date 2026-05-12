from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRead(BaseModel):
    """Публичные данные пользователя, которые можно безопасно отдавать клиенту."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    is_active: bool
    is_admin: bool
    created_at: datetime


class RegisterRequest(BaseModel):
    """Данные для регистрации пользователя."""

    email: EmailStr = Field(description="Email пользователя")
    full_name: str = Field(min_length=2, max_length=255, description="Имя и фамилия пользователя")
    password: str = Field(min_length=6, max_length=128, description="Пароль для входа")


class LoginRequest(BaseModel):
    """Данные для входа пользователя."""

    email: EmailStr = Field(description="Email пользователя")
    password: str = Field(min_length=6, max_length=128, description="Пароль пользователя")


class TokenResponse(BaseModel):
    """Ответ после успешной авторизации или регистрации."""

    access_token: str
    token_type: str = "bearer"
    user: UserRead
