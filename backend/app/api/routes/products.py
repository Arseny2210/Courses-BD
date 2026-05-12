from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Product
from app.schemas.product import ProductRead

router = APIRouter(prefix="/products", tags=["Товары"])


@router.get(
    "",
    response_model=list[ProductRead],
    summary="Список товаров",
    description="Возвращает активные товары каталога. Поддерживает поиск и пагинацию.",
)
def list_products(
    search: str | None = Query(default=None, min_length=1),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[ProductRead]:
    query = select(Product).where(Product.is_active.is_(True))

    if search:
        # Поиск работает через PostgreSQL full-text search по полю search_vector.
        query = query.where(Product.search_vector.op("@@")(func.plainto_tsquery("simple", search)))

    products = db.scalars(query.order_by(Product.created_at.desc()).offset(skip).limit(limit)).all()
    return [ProductRead.model_validate(product) for product in products]


@router.get(
    "/{product_id}",
    response_model=ProductRead,
    summary="Получить товар",
    description="Возвращает один активный товар по его идентификатору.",
)
def get_product(product_id: UUID, db: Session = Depends(get_db)) -> ProductRead:
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Товар не найден")
    return ProductRead.model_validate(product)
