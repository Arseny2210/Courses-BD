# TechStore

Полноценный CRUD-интернет-магазин техники для курсовой по базам данных.

Стек:

- `PostgreSQL` как основная БД
- `Python + FastAPI + SQLAlchemy + Alembic` для API и миграций
- `Next.js` для клиентского интерфейса

Что уже реализовано:

- регистрация и вход по JWT
- первый зарегистрированный пользователь получает роль администратора
- каталог товаров с поиском
- корзина: добавить, изменить количество, удалить, очистить
- оформление заказа
- просмотр своих заказов и отслеживание статуса готовности
- админка для полного CRUD по товарам
- админка для смены статусов заказов
- миграции, ограничения, индексы, PostgreSQL-функции и триггеры

## Структура

- [backend](/Users/arseny/Documents/New project/backend) - API, модели, миграции
- [frontend](/Users/arseny/Documents/New project/frontend) - интерфейс на Next.js

## Фишки по БД

В первой миграции уже есть:

- расширение `pgcrypto`
- функция `generate_order_number()`
- функция и триггеры `set_updated_at()`
- `UUID` первичные ключи
- `CHECK`-ограничения на цену, остаток и количество
- `UNIQUE`-ограничения
- полнотекстовый поиск по товарам через `tsvector`
- `GIN`-индекс для поиска по каталогу
- вычисляемое поле `line_total` у позиций заказа

## Локальный запуск

### 1. Создай базу данных

```sql
CREATE DATABASE tech_store;
```

### 2. Подними backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

API будет доступен на `http://127.0.0.1:8000`.

### 3. Подними frontend

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Сайт будет доступен на `http://localhost:3000`.

## Основные маршруты API

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET /api/products`
- `GET /api/products/{product_id}`
- `GET /api/cart`
- `POST /api/cart/items`
- `PATCH /api/cart/items/{item_id}`
- `DELETE /api/cart/items/{item_id}`
- `DELETE /api/cart`
- `GET /api/orders`
- `POST /api/orders`
- `GET /api/orders/{order_id}`
- `PATCH /api/orders/{order_id}/cancel`
- `GET /api/admin/products`
- `POST /api/admin/products`
- `PATCH /api/admin/products/{product_id}`
- `DELETE /api/admin/products/{product_id}`
- `GET /api/admin/orders`
- `PATCH /api/admin/orders/{order_id}`

## Что показать на защите

Для демонстрации курсовой удобно показать:

1. миграцию [0001_create_store_schema.py](/Users/arseny/Documents/New project/backend/alembic/versions/0001_create_store_schema.py)
2. модели и связи в [models](/Users/arseny/Documents/New project/backend/app/models)
3. CRUD-роуты в [routes](/Users/arseny/Documents/New project/backend/app/api/routes)
4. админскую страницу [page.tsx](/Users/arseny/Documents/New project/frontend/app/admin/page.tsx)
# Courses-BD
