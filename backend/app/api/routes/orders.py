from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.api.routes.cart import load_cart
from app.db.session import get_db
from app.models import Order, OrderItem, OrderStatus, Product, User
from app.schemas.order import OrderCreate, OrderItemRead, OrderRead

router = APIRouter(prefix="/orders", tags=["Заказы"])


def serialize_order(order: Order) -> OrderRead:
    items = [
        OrderItemRead(
            id=item.id,
            product_id=item.product_id,
            product_name=item.product_name,
            unit_price=item.unit_price,
            quantity=item.quantity,
            line_total=item.line_total or (item.unit_price * item.quantity),
        )
        for item in order.items
    ]

    return OrderRead(
        id=order.id,
        order_number=order.order_number,
        recipient_name=order.recipient_name,
        delivery_address=order.delivery_address,
        customer_phone=order.customer_phone,
        comment=order.comment,
        status=order.status,
        total_amount=order.total_amount,
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=items,
    )


def get_order_for_user(db: Session, order_id: UUID, user: User) -> Order:
    order = db.scalar(
        select(Order)
        .where(Order.id == order_id, Order.user_id == user.id)
        .options(selectinload(Order.items))
    )
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")
    return order


@router.get(
    "",
    response_model=list[OrderRead],
    summary="Список заказов пользователя",
    description="Возвращает все заказы текущего пользователя, отсортированные от новых к старым.",
)
def list_orders(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[OrderRead]:
    orders = db.scalars(
        select(Order)
        .where(Order.user_id == current_user.id)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
    ).all()
    return [serialize_order(order) for order in orders]


@router.get(
    "/{order_id}",
    response_model=OrderRead,
    summary="Получить заказ",
    description="Возвращает один заказ текущего пользователя вместе с позициями заказа.",
)
def get_order(order_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> OrderRead:
    return serialize_order(get_order_for_user(db, order_id, current_user))


@router.post(
    "",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Оформить заказ",
    description="Создаёт заказ на основе текущей корзины, уменьшает остатки товаров и очищает корзину.",
)
def create_order(
    payload: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrderRead:
    cart = load_cart(db, current_user.id)
    if not cart.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Корзина пуста")

    total_amount = Decimal("0.00")
    for item in cart.items:
        if not item.product.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Товар '{item.product.name}' больше недоступен",
            )
        if item.quantity > item.product.stock:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Недостаточно остатка для товара '{item.product.name}'",
            )
        total_amount += item.product.price * item.quantity

    # Создаём заказ и затем переносим в него все позиции из корзины.
    order = Order(
        user_id=current_user.id,
        recipient_name=payload.recipient_name.strip(),
        delivery_address=payload.delivery_address.strip(),
        customer_phone=payload.customer_phone.strip(),
        comment=payload.comment.strip() if payload.comment else None,
        total_amount=total_amount,
    )
    db.add(order)
    db.flush()

    for item in list(cart.items):
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                product_name=item.product.name,
                unit_price=item.product.price,
                quantity=item.quantity,
            )
        )
        item.product.stock -= item.quantity
        db.delete(item)

    db.commit()

    created_order = db.scalar(select(Order).where(Order.id == order.id).options(selectinload(Order.items)))
    return serialize_order(created_order)


@router.patch(
    "/{order_id}/cancel",
    response_model=OrderRead,
    summary="Отменить заказ",
    description="Отменяет заказ, если это ещё разрешено, и возвращает товары на склад.",
)
def cancel_order(order_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> OrderRead:
    order = get_order_for_user(db, order_id, current_user)
    if order.status not in {OrderStatus.pending, OrderStatus.processing}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Этот заказ уже нельзя отменить")

    order.status = OrderStatus.cancelled
    # При отмене заказа возвращаем товары обратно на склад.
    for item in order.items:
        product = db.get(Product, item.product_id)
        if product is not None:
            product.stock += item.quantity

    db.commit()
    updated_order = db.scalar(select(Order).where(Order.id == order.id).options(selectinload(Order.items)))
    return serialize_order(updated_order)
