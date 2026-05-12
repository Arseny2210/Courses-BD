from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_admin
from app.api.routes.orders import serialize_order
from app.core.utils import normalize_slug
from app.db.session import get_db
from app.models import CartItem, Order, OrderItem, OrderStatus, Product, User
from app.schemas.order import OrderRead, OrderStatusUpdate
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate

router = APIRouter(prefix="/admin", tags=["Панель управления"])


def ensure_unique_slug(db: Session, raw_slug: str, product_id: UUID | None = None) -> str:
    # Если slug уже занят, добавляем числовой суффикс.
    base_slug = normalize_slug(raw_slug)
    candidate = base_slug
    suffix = 1

    while True:
        query = select(Product).where(func.lower(Product.slug) == candidate.lower())
        if product_id is not None:
            query = query.where(Product.id != product_id)
        existing_product = db.scalar(query)
        if existing_product is None:
            return candidate
        candidate = f"{base_slug}-{suffix}"
        suffix += 1


@router.get(
    "/products",
    response_model=list[ProductRead],
    summary="Список товаров для администратора",
    description="Возвращает все товары каталога. Можно включать и скрытые товары.",
)
def admin_list_products(
    include_inactive: bool = Query(default=True),
    admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[ProductRead]:
    del admin_user

    query = select(Product)
    if not include_inactive:
        query = query.where(Product.is_active.is_(True))

    products = db.scalars(query.order_by(Product.created_at.desc())).all()
    return [ProductRead.model_validate(product) for product in products]


@router.post(
    "/products",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать товар",
    description="Создаёт новый товар в каталоге.",
)
def create_product(
    payload: ProductCreate,
    admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> ProductRead:
    del admin_user

    slug = ensure_unique_slug(db, payload.slug or payload.name)
    product = Product(
        name=payload.name.strip(),
        slug=slug,
        description=payload.description.strip(),
        price=payload.price,
        stock=payload.stock,
        image_url=payload.image_url,
        is_active=payload.is_active,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return ProductRead.model_validate(product)


@router.patch(
    "/products/{product_id}",
    response_model=ProductRead,
    summary="Обновить товар",
    description="Изменяет название, описание, цену, остаток, ссылку на изображение и другие поля товара.",
)
def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> ProductRead:
    del admin_user

    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Товар не найден")

    updates = payload.model_dump(exclude_unset=True)
    for field_name, value in updates.items():
        if field_name == "slug" and value is not None:
            setattr(product, "slug", ensure_unique_slug(db, value, product_id=product_id))
        elif field_name == "name" and value is not None:
            setattr(product, field_name, value.strip())
        elif field_name == "description" and value is not None:
            setattr(product, field_name, value.strip())
        else:
            setattr(product, field_name, value)

    db.commit()
    db.refresh(product)
    return ProductRead.model_validate(product)


@router.delete(
    "/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Удалить товар",
    description="Удаляет товар из каталога, если он не используется в корзинах и заказах.",
)
def delete_product(
    product_id: UUID,
    admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> Response:
    del admin_user

    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Товар не найден")

    cart_usage = db.scalar(select(func.count()).select_from(CartItem).where(CartItem.product_id == product.id)) or 0
    order_usage = db.scalar(select(func.count()).select_from(OrderItem).where(OrderItem.product_id == product.id)) or 0
    if cart_usage or order_usage:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Товар уже используется в корзинах или заказах. Лучше скрыть его, чем удалять.",
        )

    db.delete(product)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/orders",
    response_model=list[OrderRead],
    summary="Список всех заказов",
    description="Возвращает все заказы для панели управления.",
)
def admin_list_orders(
    admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[OrderRead]:
    del admin_user

    orders = db.scalars(select(Order).options(selectinload(Order.items)).order_by(Order.created_at.desc())).all()
    return [serialize_order(order) for order in orders]


@router.patch(
    "/orders/{order_id}",
    response_model=OrderRead,
    summary="Изменить статус заказа",
    description="Позволяет сотруднику сменить статус заказа и при необходимости вернуть товары на склад.",
)
def admin_update_order_status(
    order_id: UUID,
    payload: OrderStatusUpdate,
    admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> OrderRead:
    del admin_user

    order = db.scalar(select(Order).where(Order.id == order_id).options(selectinload(Order.items)))
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")

    if order.status == OrderStatus.cancelled and payload.status != OrderStatus.cancelled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Отменённый заказ нельзя вернуть в активный статус",
        )

    # Если заказ переводят в отменённые, товары возвращаются на склад.
    if payload.status == OrderStatus.cancelled and order.status != OrderStatus.cancelled:
        for item in order.items:
            product = db.get(Product, item.product_id)
            if product is not None:
                product.stock += item.quantity

    order.status = payload.status
    db.commit()
    refreshed_order = db.scalar(select(Order).where(Order.id == order_id).options(selectinload(Order.items)))
    return serialize_order(refreshed_order)
