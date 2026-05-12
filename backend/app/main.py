from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select

from app.api.router import api_router
from app.core.config import get_settings
from app.core.utils import normalize_slug
from app.db.session import SessionLocal
from app.models import Product

settings = get_settings()

app = FastAPI(
    title="API магазина техники",
    description="API для каталога товаров, корзины, заказов и панели управления.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def seed_products() -> None:
    # Наполняем каталог начальными товарами, если база пока пустая.
    demo_products = [
        {
            "name": "MacBook Air M3",
            "description": "Тонкий ноутбук для учёбы, программирования и повседневной работы.",
            "price": Decimal("149990.00"),
            "stock": 7,
            "image_url": "https://images.unsplash.com/photo-1517336714739-489689fd1ca8?auto=format&fit=crop&w=900&q=80",
        },
        {
            "name": "iPhone 16",
            "description": "Современный смартфон с хорошей камерой и быстрой работой приложений.",
            "price": Decimal("99990.00"),
            "stock": 12,
            "image_url": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=900&q=80",
        },
        {
            "name": "Sony WH-1000XM5",
            "description": "Беспроводные наушники с активным шумоподавлением для музыки и работы.",
            "price": Decimal("34990.00"),
            "stock": 20,
            "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=900&q=80",
        },
        {
            "name": "PlayStation 5 Slim",
            "description": "Игровая консоль нового поколения для дома и отдыха.",
            "price": Decimal("68990.00"),
            "stock": 5,
            "image_url": "https://images.unsplash.com/photo-1606813907291-d86efa9b94db?auto=format&fit=crop&w=900&q=80",
        },
        {
            "name": "Samsung Odyssey G5",
            "description": "Игровой монитор 27 дюймов с высокой частотой обновления.",
            "price": Decimal("28990.00"),
            "stock": 9,
            "image_url": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=900&q=80",
        },
        {
            "name": "Logitech MX Master 3S",
            "description": "Удобная мышь для офиса, монтажа и работы с большим количеством окон.",
            "price": Decimal("12990.00"),
            "stock": 18,
            "image_url": "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?auto=format&fit=crop&w=900&q=80",
        },
    ]

    db = SessionLocal()
    try:
        products_count = db.scalar(select(func.count()).select_from(Product)) or 0
        if products_count:
            return

        for item in demo_products:
            db.add(
                Product(
                    name=item["name"],
                    slug=normalize_slug(item["name"]),
                    description=item["description"],
                    price=item["price"],
                    stock=item["stock"],
                    image_url=item["image_url"],
                )
            )

        db.commit()
    finally:
        db.close()


@app.on_event("startup")
def on_startup() -> None:
    seed_products()


@app.get("/api/health", summary="Проверка состояния API", description="Возвращает простой ответ, что сервер запущен.")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router, prefix=settings.api_prefix)
