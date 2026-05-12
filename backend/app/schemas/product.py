from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    """Базовая схема товара."""

    name: str = Field(min_length=2, max_length=255, description="Название товара")
    slug: str | None = Field(default=None, max_length=255, description="Человекочитаемый идентификатор товара")
    description: str = Field(min_length=10, description="Описание товара")
    price: Decimal = Field(ge=0, description="Цена товара")
    stock: int = Field(ge=0, description="Количество товара на складе")
    image_url: str | None = Field(default=None, description="Ссылка на изображение товара")
    is_active: bool = Field(default=True, description="Показывать ли товар в каталоге")


class ProductCreate(ProductBase):
    """Данные для создания нового товара."""


class ProductUpdate(BaseModel):
    """Данные для частичного обновления товара."""

    name: str | None = Field(default=None, min_length=2, max_length=255, description="Новое название товара")
    slug: str | None = Field(default=None, max_length=255, description="Новый slug товара")
    description: str | None = Field(default=None, min_length=10, description="Новое описание товара")
    price: Decimal | None = Field(default=None, ge=0, description="Новая цена товара")
    stock: int | None = Field(default=None, ge=0, description="Новый остаток товара на складе")
    image_url: str | None = Field(default=None, description="Новая ссылка на изображение")
    is_active: bool | None = Field(default=None, description="Статус видимости товара в каталоге")


class ProductRead(ProductBase):
    """Схема товара, которую API возвращает клиенту."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="Идентификатор товара")
    created_at: datetime = Field(description="Дата создания товара")
    updated_at: datetime = Field(description="Дата последнего обновления товара")
