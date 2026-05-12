from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class CartItemCreate(BaseModel):
    """Данные для добавления товара в корзину."""

    product_id: UUID = Field(description="Идентификатор товара")
    quantity: int = Field(default=1, ge=1, description="Количество товара")


class CartItemUpdate(BaseModel):
    """Данные для изменения количества товара в корзине."""

    quantity: int = Field(ge=1, description="Новое количество товара")


class CartItemRead(BaseModel):
    """Одна позиция в корзине."""

    id: UUID = Field(description="Идентификатор позиции корзины")
    product_id: UUID = Field(description="Идентификатор товара")
    product_name: str = Field(description="Название товара")
    product_price: Decimal = Field(description="Цена за одну единицу товара")
    image_url: str | None = Field(description="Ссылка на изображение товара")
    stock: int = Field(description="Текущий остаток товара на складе")
    quantity: int = Field(description="Количество выбранного товара")
    line_total: Decimal = Field(description="Итоговая сумма по позиции")


class CartRead(BaseModel):
    """Корзина пользователя вместе с товарами и итогами."""

    id: UUID = Field(description="Идентификатор корзины")
    items: list[CartItemRead] = Field(description="Список товаров в корзине")
    total_items: int = Field(description="Общее количество товаров в корзине")
    total_amount: Decimal = Field(description="Общая сумма корзины")
