from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Cart, CartItem, Product, User
from app.schemas.cart import CartItemCreate, CartItemRead, CartItemUpdate, CartRead

router = APIRouter(prefix="/cart", tags=["Корзина"])


def load_cart(db: Session, user_id: UUID) -> Cart:
    # Загружаем корзину вместе с товарами внутри неё.
    cart = db.scalar(
        select(Cart)
        .where(Cart.user_id == user_id)
        .options(selectinload(Cart.items).joinedload(CartItem.product))
    )
    if cart is None:
        # Если корзины ещё нет, создаём её автоматически.
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
        cart = db.scalar(
            select(Cart)
            .where(Cart.user_id == user_id)
            .options(selectinload(Cart.items).joinedload(CartItem.product))
        )
    return cart


def serialize_cart(cart: Cart) -> CartRead:
    # Собираем ответ API в удобном для фронтенда виде.
    total_amount = Decimal("0.00")
    total_items = 0
    items: list[CartItemRead] = []

    for item in cart.items:
        line_total = item.product.price * item.quantity
        total_amount += line_total
        total_items += item.quantity
        items.append(
            CartItemRead(
                id=item.id,
                product_id=item.product_id,
                product_name=item.product.name,
                product_price=item.product.price,
                image_url=item.product.image_url,
                stock=item.product.stock,
                quantity=item.quantity,
                line_total=line_total,
            )
        )

    return CartRead(id=cart.id, items=items, total_items=total_items, total_amount=total_amount)


def get_user_cart_item(db: Session, user_id: UUID, item_id: UUID) -> CartItem:
    cart_item = db.scalar(
        select(CartItem)
        .join(Cart)
        .where(Cart.user_id == user_id, CartItem.id == item_id)
        .options(joinedload(CartItem.product))
    )
    if cart_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Позиция корзины не найдена")
    return cart_item


@router.get(
    "",
    response_model=CartRead,
    summary="Получить корзину",
    description="Возвращает корзину текущего пользователя вместе с товарами и итоговой суммой.",
)
def get_cart(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CartRead:
    cart = load_cart(db, current_user.id)
    return serialize_cart(cart)


@router.post(
    "/items",
    response_model=CartRead,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить товар в корзину",
    description="Добавляет товар в корзину. Если товар уже есть, увеличивает его количество.",
)
def add_to_cart(
    payload: CartItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CartRead:
    product = db.get(Product, payload.product_id)
    if product is None or not product.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Товар не найден")

    cart = load_cart(db, current_user.id)
    existing_item = next((item for item in cart.items if item.product_id == product.id), None)
    requested_quantity = payload.quantity + (existing_item.quantity if existing_item else 0)
    if requested_quantity > product.stock:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недостаточно товара на складе")

    if existing_item:
        existing_item.quantity = requested_quantity
    else:
        db.add(CartItem(cart_id=cart.id, product_id=product.id, quantity=payload.quantity))

    db.commit()
    return serialize_cart(load_cart(db, current_user.id))


@router.patch(
    "/items/{item_id}",
    response_model=CartRead,
    summary="Изменить количество товара",
    description="Обновляет количество выбранного товара в корзине.",
)
def update_cart_item(
    item_id: UUID,
    payload: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CartRead:
    cart_item = get_user_cart_item(db, current_user.id, item_id)
    if payload.quantity > cart_item.product.stock:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недостаточно товара на складе")

    cart_item.quantity = payload.quantity
    db.commit()
    return serialize_cart(load_cart(db, current_user.id))


@router.delete(
    "/items/{item_id}",
    response_model=CartRead,
    summary="Удалить товар из корзины",
    description="Удаляет одну позицию из корзины пользователя.",
)
def delete_cart_item(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CartRead:
    cart_item = get_user_cart_item(db, current_user.id, item_id)
    db.delete(cart_item)
    db.commit()
    return serialize_cart(load_cart(db, current_user.id))


@router.delete(
    "",
    response_model=CartRead,
    summary="Очистить корзину",
    description="Удаляет все товары из корзины текущего пользователя.",
)
def clear_cart(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CartRead:
    cart = load_cart(db, current_user.id)
    for item in list(cart.items):
        db.delete(item)
    db.commit()
    return serialize_cart(load_cart(db, current_user.id))
