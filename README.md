# Courses-BD

**Интернет-магазин техники** — курсовая работа по базам данных.
Полноценное CRUD-приложение с расширенными возможностями PostgreSQL: триггеры, функции, представления, материализованное представление, различные типы индексов, таблица аудита и вычисляемые колонки.

---

## Стек технологий

| Компонент | Технология |
|---|---|
| База данных | **PostgreSQL 16** |
| Бэкенд | **Python 3.12+ / FastAPI / SQLAlchemy 2.0 / Alembic** |
| Фронтенд | **Next.js 15 / React 19 / TypeScript** |
| Аутентификация | JWT (python-jose) + bcrypt |
| Драйвер БД | psycopg 3 |

---

## Модели данных (таблицы)

### 1. `users` — пользователи

| Колонка | Тип | Ограничения |
|---|---|---|
| id | UUID | PK, `gen_random_uuid()` |
| email | VARCHAR(255) | NOT NULL |
| full_name | VARCHAR(255) | NOT NULL |
| hashed_password | VARCHAR(255) | NOT NULL |
| is_active | BOOLEAN | DEFAULT TRUE |
| is_admin | BOOLEAN | DEFAULT FALSE |
| created_at | TIMESTAMPTZ | `CURRENT_TIMESTAMP` |
| updated_at | TIMESTAMPTZ | `CURRENT_TIMESTAMP` |

**Связи:** 1:1 с корзиной, 1:M с заказами

### 2. `products` — товары

| Колонка | Тип | Ограничения |
|---|---|---|
| id | UUID | PK, `gen_random_uuid()` |
| name | VARCHAR(255) | NOT NULL |
| slug | VARCHAR(255) | NOT NULL, UNIQUE |
| description | TEXT | NOT NULL |
| price | NUMERIC(10,2) | CHECK >= 0 |
| stock | INTEGER | DEFAULT 0, CHECK >= 0 |
| image_url | TEXT | |
| is_active | BOOLEAN | DEFAULT TRUE |
| search_vector | TSVECTOR | **вычисляемая** persisted |
| created_at | TIMESTAMPTZ | `CURRENT_TIMESTAMP` |
| updated_at | TIMESTAMPTZ | `CURRENT_TIMESTAMP` |

**Вычисляемая колонка:**
```sql
search_vector TSVECTOR GENERATED ALWAYS AS (
    to_tsvector('simple', coalesce(name, '') || ' ' || coalesce(description, ''))
) STORED
```

### 3. `carts` — корзины

| Колонка | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → users, UNIQUE, CASCADE |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### 4. `cart_items` — позиции корзины

| Колонка | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| cart_id | UUID | FK → carts, CASCADE |
| product_id | UUID | FK → products, RESTRICT |
| quantity | INTEGER | CHECK > 0 |
| UNIQUE | (cart_id, product_id) | |

### 5. `orders` — заказы

| Колонка | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → users, CASCADE |
| order_number | VARCHAR(32) | UNIQUE, `generate_order_number()` |
| recipient_name | VARCHAR(255) | NOT NULL |
| delivery_address | TEXT | NOT NULL |
| customer_phone | VARCHAR(32) | NOT NULL |
| comment | TEXT | |
| status | order_status | ENUM, DEFAULT 'pending' |
| total_amount | NUMERIC(12,2) | CHECK >= 0 |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

**ENUM `order_status`:** `pending`, `processing`, `ready_for_pickup`, `completed`, `cancelled`

### 6. `order_items` — позиции заказа

| Колонка | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| order_id | UUID | FK → orders, CASCADE |
| product_id | UUID | FK → products, RESTRICT |
| product_name | VARCHAR(255) | NOT NULL |
| unit_price | NUMERIC(10,2) | CHECK >= 0 |
| quantity | INTEGER | CHECK > 0 |
| line_total | NUMERIC(12,2) | **вычисляемая** persisted |
| created_at | TIMESTAMPTZ | |

**Вычисляемая колонка:**
```sql
line_total NUMERIC(12,2) GENERATED ALWAYS AS (ROUND(unit_price * quantity, 2)) STORED
```

### 7. `order_status_log` — аудит изменений статусов (добавлена в миграции 0002)

| Колонка | Тип | Ограничения |
|---|---|---|
| id | UUID | PK, `gen_random_uuid()` |
| order_id | UUID | FK → orders, CASCADE |
| old_status | order_status | |
| new_status | order_status | NOT NULL |
| changed_by | UUID | FK → users |
| changed_at | TIMESTAMPTZ | DEFAULT NOW() |

---

## Триггеры (всего 9 шт.)

### Миграция 0001 — базовые триггеры

#### 🔹 `trg_{table}_updated_at` (5 триггеров)

Срабатывает на таблицах: `users`, `products`, `carts`, `cart_items`, `orders`

| Параметр | Значение |
|---|---|
| Момент | `BEFORE UPDATE` |
| Функция | `set_updated_at()` |
| Действие | `NEW.updated_at = CURRENT_TIMESTAMP` |

Автоматически обновляет поле `updated_at` при любом изменении записи.

---

### Миграция 0002 — дополнительные триггеры

#### 🔹 `trg_orders_status_change` — логирование смены статуса

| Параметр | Значение |
|---|---|
| Таблица | `orders` |
| Момент | `AFTER UPDATE OF status` |
| Функция | `log_order_status_change()` |
| Действие | Вставляет запись в `order_status_log` |

```sql
-- Пример: админ меняет статус
UPDATE orders SET status = 'processing' WHERE id = '...';
-- Автоматически:
-- INSERT INTO order_status_log (order_id, old_status, new_status)
-- VALUES ('...', 'pending', 'processing');
```

#### 🔹 `trg_orders_status_validate` — валидация переходов статуса

| Параметр | Значение |
|---|---|
| Таблица | `orders` |
| Момент | `BEFORE UPDATE OF status` |
| Функция | `validate_order_status_transition()` |
| Действие | Запрещает некорректные переходы |

**Запрещено:**
- Менять статус отменённого заказа (`cancelled`)
- Менять статус выполненного заказа (`completed`)

```sql
UPDATE orders SET status = 'processing' WHERE status = 'cancelled';
-- ERROR: Нельзя изменить статус отменённого заказа
```

#### 🔹 `trg_users_admin_protect` — защита последнего администратора

| Параметр | Значение |
|---|---|
| Таблица | `users` |
| Момент | `BEFORE UPDATE OF is_admin, is_active` |
| Функция | `prevent_last_admin_deactivation()` |
| Действие | Блокирует снятие прав/деактивацию последнего админа |

```sql
UPDATE users SET is_admin = FALSE WHERE id = '...';
-- ERROR, если это был последний админ:
-- Нельзя снять права администратора с последнего администратора

UPDATE users SET is_active = FALSE WHERE is_admin = TRUE;
-- ERROR, если это был последний активный админ:
-- Нельзя деактивировать последнего активного администратора
```

---

## Функции PostgreSQL

### Миграция 0001

#### 🔹 `set_updated_at()`

```sql
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

**Тип:** триггерная
**Используется в:** триггерах `trg_{table}_updated_at` на всех 5 таблицах

#### 🔹 `generate_order_number()`

```sql
CREATE OR REPLACE FUNCTION generate_order_number()
RETURNS TEXT AS $$
BEGIN
    RETURN 'ORD-' ||
        TO_CHAR(CURRENT_TIMESTAMP, 'YYYYMMDD') ||
        '-' ||
        UPPER(SUBSTRING(ENCODE(gen_random_bytes(4), 'hex') FROM 1 FOR 6));
END;
$$ LANGUAGE plpgsql VOLATILE;
```

**Тип:** VOLATILE (возвращает разное значение при каждом вызове)
**Формат:** `ORD-20260406-AB3F9C`
**Используется в:** `DEFAULT generate_order_number()` для `orders.order_number`

---

### Миграция 0002

#### 🔹 `search_products_ranked(search_term TEXT)`

| Параметр | Значение |
|---|---|
| Тип | `STABLE` |
| Возвращает | `TABLE(id UUID, name, slug, description, price, stock, rank REAL)` |
| Язык | plpgsql |

**Описание:** Полнотекстовый поиск по товарам с ранжированием результата по релевантности.

**Алгоритм:**
1. Преобразует строку поиска в `tsquery` через `plainto_tsquery('simple', search_term)`
2. Ищет совпадения по полю `search_vector` (TSVECTOR, GIN-индекс)
3. Сортирует по `ts_rank` (убывание) и цене (возрастание)
4. Возвращает только активные товары (`is_active = TRUE`)

**Пример:**
```sql
SELECT * FROM search_products_ranked('sony');
-- id | name           | price  | stock | rank
-- …  | Sony WH-1000XM5| 34990  | 15    | 0.0608
```

---

#### 🔹 `get_popular_products(max_count INTEGER DEFAULT 10)`

| Параметр | Значение |
|---|---|
| Тип | `STABLE` |
| Возвращает | `JSON` |

**Описание:** Возвращает JSON-массив популярных товаров на основе реальных продаж (из `order_items`).

**Поля в JSON:**
```json
[
  {
    "id": "uuid",
    "name": "Logitech MX Master 3S",
    "slug": "logitech-mx-master-3s",
    "price": 12990.00,
    "total_sold": 3,
    "order_count": 1
  }
]
```

**Логика:**
- Собирает `SUM(quantity)` и `COUNT(DISTINCT order_id)` из `order_items`
- Исключает отменённые заказы (`status != 'cancelled'`)
- Фильтрует только активные товары
- Сортирует по убыванию проданного количества

---

#### 🔹 `get_user_order_stats(p_user_id UUID)`

| Параметр | Значение |
|---|---|
| Тип | `STABLE` |
| Возвращает | `JSON` |

**Описание:** Возвращает JSON со статистикой заказов пользователя.

**Поля:**
```json
{
  "total_orders": 5,
  "total_spent": 134980.00,
  "avg_order_amount": 26996.00,
  "max_order_amount": 68990.00,
  "status_breakdown": {
    "pending": 2,
    "completed": 2,
    "cancelled": 1
  },
  "last_order_date": "2026-04-07T13:39:32.127481+03:00"
}
```

**Логика:**
- Считает общее количество и сумму заказов
- Группирует по статусу (`JSON_OBJECT_AGG`)
- Находит средний и максимальный чек
- Определяет дату последнего заказа

---

#### 🔹 `get_dashboard_metrics()`

| Параметр | Значение |
|---|---|
| Тип | `STABLE` |
| Возвращает | `JSON` |

**Описание:** Агрегирует 8 ключевых метрик для админ-панели в одном запросе.

**Поля:**
```json
{
  "total_products": 6,
  "total_users": 10,
  "total_orders": 25,
  "revenue_total": 450000.00,
  "revenue_today": 0,
  "pending_orders": 3,
  "processing_orders": 2,
  "ready_for_pickup": 1,
  "top_products": [...]
}
```

**Что делает внутри (8 подзапросов):**
| Метрика | Запрос |
|---|---|
| total_products | `COUNT(*) FROM products WHERE is_active = TRUE` |
| total_users | `COUNT(*) FROM users` |
| total_orders | `COUNT(*) FROM orders` |
| revenue_total | `SUM(total_amount) WHERE status NOT IN ('cancelled')` |
| revenue_today | `SUM(total_amount) WHERE NOT cancelled AND created_at >= CURRENT_DATE` |
| pending_orders | `COUNT(*) WHERE status = 'pending'` |
| processing_orders | `COUNT(*) WHERE status = 'processing'` |
| ready_for_pickup | `COUNT(*) WHERE status = 'ready_for_pickup'` |
| top_products | вызов `get_popular_products(5)` |

---

#### 🔹 `calculate_cart_total(p_cart_id UUID)`

| Параметр | Значение |
|---|---|
| Тип | `VOLATILE` |
| Возвращает | `NUMERIC(12,2)` |

**Описание:** Рассчитывает общую сумму корзины: цена × количество по всем позициям.

```sql
SELECT calculate_cart_total('uuid-корзины');
-- 12990.00
```

---

#### 🔹 `refresh_popular_products()` — для автообновления материализованного представления

| Параметр | Значение |
|---|---|
| Тип | триггерная |
| Возвращает | `TRIGGER` |

```sql
CREATE OR REPLACE FUNCTION refresh_popular_products()
RETURNS TRIGGER AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_popular_products;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
```

Может быть использована для автообновления: навесить триггер на `order_items` или `orders`.

---

### Сводка всех функций

| Функция | Тип | Возвращает | Миграция |
|---|---|---|---|
| `set_updated_at()` | триггерная | TRIGGER | 0001 |
| `generate_order_number()` | VOLATILE | TEXT | 0001 |
| `log_order_status_change()` | триггерная | TRIGGER | 0002 |
| `prevent_last_admin_deactivation()` | триггерная | TRIGGER | 0002 |
| `validate_order_status_transition()` | триггерная | TRIGGER | 0002 |
| `search_products_ranked(TEXT)` | STABLE | TABLE | 0002 |
| `get_popular_products(INTEGER)` | STABLE | JSON | 0002 |
| `get_user_order_stats(UUID)` | STABLE | JSON | 0002 |
| `get_dashboard_metrics()` | STABLE | JSON | 0002 |
| `calculate_cart_total(UUID)` | VOLATILE | NUMERIC | 0002 |
| `refresh_popular_products()` | триггерная | TRIGGER | 0002 |

---

## Представления (Views)

### 👁 `vw_active_products`

```sql
CREATE OR REPLACE VIEW vw_active_products AS
SELECT id, name, slug, description, price, stock, image_url, created_at, updated_at
FROM products
WHERE is_active = TRUE;
```

Показывает только активные товары без технического поля `is_active` и `search_vector`.

---

### 👁 `vw_order_audit`

```sql
CREATE OR REPLACE VIEW vw_order_audit AS
SELECT
    o.id AS order_id, o.order_number,
    u.email AS user_email, u.full_name AS user_name,
    osl.old_status, osl.new_status, osl.changed_at, osl.changed_by
FROM orders o
JOIN users u ON u.id = o.user_id
LEFT JOIN order_status_log osl ON osl.order_id = o.id;
```

Полная история изменений статусов заказов. Соединяет 3 таблицы.

| Ситуация | Результат |
|---|---|
| У заказа нет изменений статуса | 1 строка с NULL-полями |
| У заказа 3 смены статуса | 3 строки |
| Заказ удалён | Пропадает из представления |

---

### 👁 `vw_user_order_summary`

```sql
CREATE OR REPLACE VIEW vw_user_order_summary AS
SELECT
    u.id AS user_id, u.email, u.full_name, u.created_at AS registered_at,
    COUNT(o.id) AS total_orders,
    COALESCE(SUM(o.total_amount), 0) AS total_spent,
    COALESCE(AVG(o.total_amount), 0) AS avg_order_amount,
    MAX(o.created_at) AS last_order_date,
    CASE
        WHEN COUNT(o.id) = 0 THEN 'never_ordered'
        WHEN MAX(o.created_at) >= CURRENT_DATE - INTERVAL '30 days' THEN 'active'
        WHEN MAX(o.created_at) >= CURRENT_DATE - INTERVAL '90 days' THEN 'recent'
        ELSE 'dormant'
    END AS customer_segment
FROM users u
LEFT JOIN orders o ON o.user_id = u.id
GROUP BY u.id, u.email, u.full_name, u.created_at;
```

**Сегментация клиентов:**

| Сегмент | Условие | Маркетинговое действие |
|---|---|---|
| `never_ordered` | Нет заказов | Отправить промокод |
| `active` | Заказ за 30 дней | Лояльный клиент |
| `recent` | Заказ за 90 дней | Напомнить о себе |
| `dormant` | Заказ > 90 дней назад | Вернуть скидкой |

---

## Материализованное представление

### `mv_popular_products`

```sql
CREATE MATERIALIZED VIEW mv_popular_products AS
SELECT
    p.id, p.name, p.slug, p.price, p.stock,
    COALESCE(SUM(oi.quantity), 0) AS total_sold,
    COUNT(DISTINCT oi.order_id) AS order_count,
    RANK() OVER (ORDER BY COALESCE(SUM(oi.quantity), 0) DESC) AS popularity_rank
FROM products p
LEFT JOIN order_items oi ON oi.product_id = p.id
LEFT JOIN orders o ON o.id = oi.order_id AND o.status NOT IN ('cancelled')
WHERE p.is_active = TRUE
GROUP BY p.id, p.name, p.slug, p.price, p.stock
ORDER BY total_sold DESC;
```

**Отличие от обычного представления:** данные физически сохраняются на диске.

**Индекс:** `ix_mv_popular_products_rank` — для быстрой сортировки по рангу.

**Обновление:**
```sql
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_popular_products;
```

Может автоматически обновляться через триггер на `order_items` (функция `refresh_popular_products()` готова).

---

## Индексы (всего 15 + PK)

### Миграция 0001

| Индекс | Таблица | Тип | Колонки |
|---|---|---|---|
| `ix_users_email_lower` | users | **UNIQUE, Expression** | `lower(email)` |
| `ix_products_active_price` | products | B-tree | `is_active, price` |
| `ix_products_search_vector` | products | **GIN** | `search_vector` |
| `ix_cart_items_cart_id` | cart_items | B-tree | `cart_id` |
| `ix_cart_items_product_id` | cart_items | B-tree | `product_id` |
| `ix_orders_user_created_at` | orders | B-tree | `user_id, created_at` |
| `ix_orders_status` | orders | B-tree | `status` |
| `ix_order_items_order_id` | order_items | B-tree | `order_id` |
| `ix_order_items_product_id` | order_items | B-tree | `product_id` |

### Миграция 0002

| Индекс | Таблица | Тип | Колонки | Особенность |
|---|---|---|---|---|
| `ix_orders_pending_status` | orders | **Partial** | `created_at, id` | `WHERE status = 'pending'` |
| `ix_orders_active_status` | orders | **Partial** | `created_at` | `WHERE status NOT IN ('cancelled','completed')` |
| `ix_products_name_lower` | products | **Expression** | `lower(name)` | |
| `ix_products_price_covering` | products | **Covering** | `price` | `INCLUDE (id, name, slug, stock)` |
| `ix_users_email` | users | B-tree | `email` | |
| `ix_orders_created_at` | orders | B-tree | `created_at` | |
| `ix_order_status_log_order_id` | order_status_log | B-tree | `order_id` | |
| `ix_order_status_log_changed_at` | order_status_log | B-tree | `changed_at` | |
| `ix_mv_popular_products_rank` | mv_popular_products | B-tree | `popularity_rank` | |

### Типы индексов — пояснения

| Тип | Что даёт | Пример использования |
|---|---|---|
| **B-tree** | Стандартный, для сортировки и сравнения | Почти все базовые индексы |
| **GIN** | Для полнотекстового поиска и массивов | `search_vector` — быстрый поиск по товарам |
| **Partial** | Индексирует только часть строк | `WHERE status = 'pending'` — меньше размер, быстрее поиск |
| **Expression** | Индексирует результат выражения | `lower(name)` — поиск без учёта регистра |
| **Covering** | Хранит доп. колонки в индексе | Запросы без обращения к таблице (index-only scan) |
| **Unique** | Гарантирует уникальность | `lower(email)` — защита от дублей email |

---

## CHECK-ограничения

| Имя | Таблица | Условие |
|---|---|---|
| `ck_products_price_non_negative` | products | `price >= 0` |
| `ck_products_stock_non_negative` | products | `stock >= 0` |
| `ck_cart_items_quantity_positive` | cart_items | `quantity > 0` |
| `ck_orders_total_amount_non_negative` | orders | `total_amount >= 0` |
| `ck_order_items_unit_price_non_negative` | order_items | `unit_price >= 0` |
| `ck_order_items_quantity_positive` | order_items | `quantity > 0` |

---

## Схемы взаимодействия (что происходит при действиях пользователя)

### Регистрация (`POST /api/auth/register`)
```
→ Создаётся пользователь в users
→ Если пользователь первый — is_admin = TRUE
→ Автоматически создаётся корзина в carts
```

### Поиск товаров (`GET /api/products?search=sony`)
```
→ search_products_ranked('sony')
→ ts_rank() + GIN-индекс по search_vector
→ Возвращает товары, отсортированные по релевантности
```

### Просмотр корзины
```
→ calculate_cart_total(cart_id) → сумма на лету
→ JOIN cart_items + products
```

### Смена статуса заказа (админ / отмена пользователем)
```
→ BEFORE UPDATE: trg_orders_status_validate
   ↓ проверка: не cancelled? не completed? → ок
→ UPDATE orders SET status = '...'
→ AFTER UPDATE: trg_orders_status_change
   ↓ проверка: статус реально изменился?
→ INSERT INTO order_status_log (old_status, new_status)
```

### Попытка снять права с последнего админа
```
→ UPDATE users SET is_admin = FALSE
→ BEFORE UPDATE: trg_users_admin_protect
   ↓ SELECT COUNT(*) FROM users WHERE is_admin = TRUE AND id != OLD.id
→ Если 0 → RAISE EXCEPTION
```

### Загрузка админ-дашборда
```
→ get_dashboard_metrics()
→ 8 метрик за 1 запрос (включая вызов get_popular_products(5))
```

---

## API Endpoints

### Авторизация
| Метод | Путь | Описание |
|---|---|---|
| POST | `/api/auth/register` | Регистрация |
| POST | `/api/auth/login` | Вход |
| GET | `/api/auth/me` | Текущий пользователь |

### Товары (публичные)
| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/products` | Список товаров (+ поиск ?search=) |
| GET | `/api/products/{id}` | Детально о товаре |

### Корзина
| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/cart` | Корзина с суммой |
| POST | `/api/cart/items` | Добавить товар |
| PATCH | `/api/cart/items/{id}` | Изменить количество |
| DELETE | `/api/cart/items/{id}` | Удалить позицию |
| DELETE | `/api/cart` | Очистить корзину |

### Заказы
| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/orders` | Мои заказы |
| POST | `/api/orders` | Оформить заказ |
| GET | `/api/orders/{id}` | Детально |
| PATCH | `/api/orders/{id}/cancel` | Отменить |

### Админ-панель
| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/admin/products` | Все товары |
| POST | `/api/admin/products` | Создать товар |
| PATCH | `/api/admin/products/{id}` | Обновить товар |
| DELETE | `/api/admin/products/{id}` | Удалить товар |
| GET | `/api/admin/orders` | Все заказы |
| PATCH | `/api/admin/orders/{id}` | Сменить статус |

---

## Миграции

| Миграция | Описание |
|---|---|
| `0001_create_store_schema` | Базовая схема: 6 таблиц, ENUM, 2 функции, 5 триггеров, 9 индексов, CHECK, вычисляемые колонки |
| `0002_add_psql_features` | Расширенные PSQL-фичи: таблица аудита, 3 триггера, 6 функций, 3 представления, материализованное представление, 9 индексов |

---

## Локальный запуск

### 1. База данных
```sql
CREATE DATABASE tech_store;
```

### 2. Бэкенд
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Отредактировать .env под свою БД
alembic upgrade head
uvicorn app.main:app --reload
```
API: `http://127.0.0.1:8000`

### 3. Фронтенд
```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```
Сайт: `http://localhost:3000`

---

## Структура проекта

```
├── backend/
│   ├── alembic/              # Миграции БД
│   │   └── versions/
│   │       ├── 0001_create_store_schema.py
│   │       └── 0002_add_psql_features.py
│   ├── app/
│   │   ├── api/              # Маршруты API
│   │   │   └── routes/       # admin, auth, cart, orders, products
│   │   ├── core/             # config, security, utils
│   │   ├── db/               # session, base
│   │   ├── models/           # SQLAlchemy модели
│   │   └── schemas/          # Pydantic схемы
│   └── alembic.ini
├── frontend/
│   ├── app/                  # Next.js страницы
│   ├── components/           # React компоненты
│   └── lib/                  # API client, types
└── docs/
    └── схема.png
```
