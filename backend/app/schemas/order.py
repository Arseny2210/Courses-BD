from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import OrderStatus


class OrderCreate(BaseModel):
    """Данные для оформления нового заказа."""

    recipient_name: str = Field(min_length=2, max_length=255, description="Имя получателя заказа")
    delivery_address: str = Field(min_length=10, description="Адрес доставки или место выдачи")
    customer_phone: str = Field(min_length=5, max_length=32, description="Телефон покупателя")
    comment: str | None = Field(default=None, max_length=1000, description="Дополнительный комментарий к заказу")


class OrderItemRead(BaseModel):
    """Одна позиция внутри оформленного заказа."""

    id: UUID = Field(description="Идентификатор позиции заказа")
    product_id: UUID = Field(description="Идентификатор товара")
    product_name: str = Field(description="Название товара на момент оформления заказа")
    unit_price: Decimal = Field(description="Цена за единицу на момент заказа")
    quantity: int = Field(description="Количество товара")
    line_total: Decimal = Field(description="Итоговая сумма по позиции")


class OrderRead(BaseModel):
    """Полные данные заказа, которые API возвращает клиенту."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="Идентификатор заказа")
    order_number: str = Field(description="Уникальный номер заказа")
    recipient_name: str = Field(description="Имя получателя")
    delivery_address: str = Field(description="Адрес доставки или место выдачи")
    customer_phone: str = Field(description="Телефон покупателя")
    comment: str | None = Field(description="Комментарий к заказу")
    status: OrderStatus = Field(description="Текущий статус заказа")
    total_amount: Decimal = Field(description="Полная сумма заказа")
    created_at: datetime = Field(description="Дата создания заказа")
    updated_at: datetime = Field(description="Дата последнего изменения заказа")
    items: list[OrderItemRead] = Field(description="Список товаров в заказе")


class OrderStatusUpdate(BaseModel):
    """Данные для смены статуса заказа сотрудником."""

    status: OrderStatus = Field(description="Новый статус заказа")
