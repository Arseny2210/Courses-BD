from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import admin, auth, cart, orders, products

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(products.router)
api_router.include_router(cart.router)
api_router.include_router(orders.router)
api_router.include_router(admin.router)

