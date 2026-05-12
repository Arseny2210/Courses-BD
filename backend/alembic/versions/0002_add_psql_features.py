"""add psql features — triggers, functions, views, materialized view, indexes

Revision ID: 0002_add_psql_features
Revises: 0001_create_store_schema
Create Date: 2026-04-06 23:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_add_psql_features"
down_revision = "0001_create_store_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─────────────────────────────────────────────────────────────────
    # 1. order_status_log — аудит изменений статуса заказа
    # ─────────────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE order_status_log (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            order_id    UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            old_status  order_status,
            new_status  order_status NOT NULL,
            changed_by  UUID REFERENCES users(id),
            changed_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    op.create_index("ix_order_status_log_order_id", "order_status_log", ["order_id"])
    op.create_index(
        "ix_order_status_log_changed_at", "order_status_log", ["changed_at"]
    )

    # ─────────────────────────────────────────────────────────────────
    # 2. Триггер: логирование смены статуса заказа
    # ─────────────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE OR REPLACE FUNCTION log_order_status_change()
        RETURNS TRIGGER AS $$
        BEGIN
            IF OLD.status IS DISTINCT FROM NEW.status THEN
                INSERT INTO order_status_log (order_id, old_status, new_status, changed_at)
                VALUES (NEW.id, OLD.status, NEW.status, CURRENT_TIMESTAMP);
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_orders_status_change
        AFTER UPDATE OF status ON orders
        FOR EACH ROW
        EXECUTE FUNCTION log_order_status_change();
        """
    )

    # ─────────────────────────────────────────────────────────────────
    # 3. Триггер: защита последнего администратора
    # ─────────────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_last_admin_deactivation()
        RETURNS TRIGGER AS $$
        DECLARE
            admin_count INTEGER;
        BEGIN
            IF OLD.is_admin = TRUE AND NEW.is_admin = FALSE THEN
                SELECT COUNT(*) INTO admin_count
                FROM users
                WHERE is_admin = TRUE AND id != OLD.id;

                IF admin_count = 0 THEN
                    RAISE EXCEPTION 'Нельзя снять права администратора с последнего администратора';
                END IF;
            END IF;

            IF OLD.is_active = TRUE AND NEW.is_active = FALSE AND OLD.is_admin = TRUE THEN
                SELECT COUNT(*) INTO admin_count
                FROM users
                WHERE is_admin = TRUE AND is_active = TRUE AND id != OLD.id;

                IF admin_count = 0 THEN
                    RAISE EXCEPTION 'Нельзя деактивировать последнего активного администратора';
                END IF;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_users_admin_protect
        BEFORE UPDATE OF is_admin, is_active ON users
        FOR EACH ROW
        EXECUTE FUNCTION prevent_last_admin_deactivation();
        """
    )

    # ─────────────────────────────────────────────────────────────────
    # 4. Триггер: валидация переходов статуса заказа
    # ─────────────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE OR REPLACE FUNCTION validate_order_status_transition()
        RETURNS TRIGGER AS $$
        BEGIN
            IF OLD.status = 'cancelled' AND NEW.status != 'cancelled' THEN
                RAISE EXCEPTION 'Нельзя изменить статус отменённого заказа';
            END IF;

            IF OLD.status = 'completed' AND NEW.status != 'completed' THEN
                RAISE EXCEPTION 'Нельзя изменить статус выполненного заказа';
            END IF;

            IF OLD.status = 'cancelled' AND NEW.status IS DISTINCT FROM OLD.status THEN
                RAISE EXCEPTION 'Нельзя изменить статус отменённого заказа';
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_orders_status_validate
        BEFORE UPDATE OF status ON orders
        FOR EACH ROW
        WHEN (OLD.status IS DISTINCT FROM NEW.status)
        EXECUTE FUNCTION validate_order_status_transition();
        """
    )

    # ─────────────────────────────────────────────────────────────────
    # 5. Функция: поиск товаров с ранжированием
    # ─────────────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE OR REPLACE FUNCTION search_products_ranked(search_term TEXT)
        RETURNS TABLE(
            id          UUID,
            name        VARCHAR(255),
            slug        VARCHAR(255),
            description TEXT,
            price       NUMERIC(10,2),
            stock       INTEGER,
            rank        REAL
        ) AS $$
        BEGIN
            RETURN QUERY
            SELECT
                p.id,
                p.name,
                p.slug,
                p.description,
                p.price,
                p.stock,
                ts_rank(p.search_vector, query) AS rank
            FROM products p,
                 plainto_tsquery('simple', search_term) AS query
            WHERE p.search_vector @@ query
              AND p.is_active = TRUE
            ORDER BY rank DESC, p.price ASC;
        END;
        $$ LANGUAGE plpgsql STABLE;
        """
    )

    # ─────────────────────────────────────────────────────────────────
    # 6. Функция: популярные товары (JSON)
    # ─────────────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE OR REPLACE FUNCTION get_popular_products(max_count INTEGER DEFAULT 10)
        RETURNS JSON AS $$
        DECLARE
            result JSON;
        BEGIN
            SELECT JSON_AGG(
                JSON_BUILD_OBJECT(
                    'id', p.id,
                    'name', p.name,
                    'slug', p.slug,
                    'price', p.price,
                    'total_sold', COALESCE(s.total_sold, 0),
                    'order_count', COALESCE(s.order_count, 0)
                )
                ORDER BY COALESCE(s.total_sold, 0) DESC
            ) INTO result
            FROM products p
            LEFT JOIN (
                SELECT
                    oi.product_id,
                    SUM(oi.quantity) AS total_sold,
                    COUNT(DISTINCT oi.order_id) AS order_count
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                WHERE o.status NOT IN ('cancelled')
                GROUP BY oi.product_id
            ) s ON s.product_id = p.id
            WHERE p.is_active = TRUE
            LIMIT max_count;

            RETURN COALESCE(result, '[]'::JSON);
        END;
        $$ LANGUAGE plpgsql STABLE;
        """
    )

    # ─────────────────────────────────────────────────────────────────
    # 7. Функция: статистика заказов пользователя (JSON)
    # ─────────────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE OR REPLACE FUNCTION get_user_order_stats(p_user_id UUID)
        RETURNS JSON AS $$
        DECLARE
            result JSON;
        BEGIN
            SELECT JSON_BUILD_OBJECT(
                'total_orders', COUNT(*),
                'total_spent', COALESCE(SUM(total_amount), 0),
                'avg_order_amount', COALESCE(ROUND(AVG(total_amount), 2), 0),
                'max_order_amount', COALESCE(MAX(total_amount), 0),
                'status_breakdown', (
                    SELECT JSON_OBJECT_AGG(status, cnt)
                    FROM (
                        SELECT status::TEXT AS status, COUNT(*) AS cnt
                        FROM orders
                        WHERE user_id = p_user_id
                        GROUP BY status
                    ) sub
                ),
                'last_order_date', MAX(created_at)
            ) INTO result
            FROM orders
            WHERE user_id = p_user_id;

            RETURN COALESCE(result, '{}'::JSON);
        END;
        $$ LANGUAGE plpgsql STABLE;
        """
    )

    # ─────────────────────────────────────────────────────────────────
    # 8. Функция: метрики для админ-дашборда (JSON)
    # ─────────────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE OR REPLACE FUNCTION get_dashboard_metrics()
        RETURNS JSON AS $$
        DECLARE
            result JSON;
        BEGIN
            SELECT JSON_BUILD_OBJECT(
                'total_products', (SELECT COUNT(*) FROM products WHERE is_active = TRUE),
                'total_users', (SELECT COUNT(*) FROM users),
                'total_orders', (SELECT COUNT(*) FROM orders),
                'revenue_total', (SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE status NOT IN ('cancelled')),
                'revenue_today', (SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE status NOT IN ('cancelled') AND created_at >= CURRENT_DATE),
                'pending_orders', (SELECT COUNT(*) FROM orders WHERE status = 'pending'),
                'processing_orders', (SELECT COUNT(*) FROM orders WHERE status = 'processing'),
                'ready_for_pickup', (SELECT COUNT(*) FROM orders WHERE status = 'ready_for_pickup'),
                'top_products', get_popular_products(5)
            ) INTO result;

            RETURN result;
        END;
        $$ LANGUAGE plpgsql STABLE;
        """
    )

    # ─────────────────────────────────────────────────────────────────
    # 9. Функция: расчёт общей суммы корзины (volatile, тк данные меняются)
    # ─────────────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE OR REPLACE FUNCTION calculate_cart_total(p_cart_id UUID)
        RETURNS NUMERIC(12,2) AS $$
        DECLARE
            total NUMERIC(12,2);
        BEGIN
            SELECT COALESCE(SUM(p.price * ci.quantity), 0) INTO total
            FROM cart_items ci
            JOIN products p ON p.id = ci.product_id
            WHERE ci.cart_id = p_cart_id;

            RETURN total;
        END;
        $$ LANGUAGE plpgsql VOLATILE;
        """
    )

    # ─────────────────────────────────────────────────────────────────
    # 10. Представления (Views)
    # ─────────────────────────────────────────────────────────────────

    # vw_active_products — только активные товары
    op.execute(
        """
        CREATE OR REPLACE VIEW vw_active_products AS
        SELECT
            id,
            name,
            slug,
            description,
            price,
            stock,
            image_url,
            created_at,
            updated_at
        FROM products
        WHERE is_active = TRUE;
        """
    )

    # vw_order_audit — заказы с историей статусов
    op.execute(
        """
        CREATE OR REPLACE VIEW vw_order_audit AS
        SELECT
            o.id AS order_id,
            o.order_number,
            u.email AS user_email,
            u.full_name AS user_name,
            osl.old_status,
            osl.new_status,
            osl.changed_at,
            osl.changed_by
        FROM orders o
        JOIN users u ON u.id = o.user_id
        LEFT JOIN order_status_log osl ON osl.order_id = o.id;
        """
    )

    # vw_user_order_summary — сводка по пользователям и их заказам
    op.execute(
        """
        CREATE OR REPLACE VIEW vw_user_order_summary AS
        SELECT
            u.id AS user_id,
            u.email,
            u.full_name,
            u.created_at AS registered_at,
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
        """
    )

    # ─────────────────────────────────────────────────────────────────
    # 11. Материализованное представление: популярные товары (кеш)
    # ─────────────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE MATERIALIZED VIEW mv_popular_products AS
        SELECT
            p.id,
            p.name,
            p.slug,
            p.price,
            p.stock,
            COALESCE(SUM(oi.quantity), 0) AS total_sold,
            COUNT(DISTINCT oi.order_id) AS order_count,
            RANK() OVER (ORDER BY COALESCE(SUM(oi.quantity), 0) DESC) AS popularity_rank
        FROM products p
        LEFT JOIN order_items oi ON oi.product_id = p.id
        LEFT JOIN orders o ON o.id = oi.order_id AND o.status NOT IN ('cancelled')
        WHERE p.is_active = TRUE
        GROUP BY p.id, p.name, p.slug, p.price, p.stock
        ORDER BY total_sold DESC;
        """
    )
    op.create_index(
        "ix_mv_popular_products_rank", "mv_popular_products", ["popularity_rank"]
    )

    # ─────────────────────────────────────────────────────────────────
    # 12. Дополнительные индексы
    # ─────────────────────────────────────────────────────────────────

    # Частичный индекс: только ожидающие заказы (ускорение работы админа)
    op.create_index(
        "ix_orders_pending_status",
        "orders",
        ["created_at", "id"],
        unique=False,
        postgresql_where=sa.text("status = 'pending'"),
    )

    # Частичный индекс: неотменённые заказы для отчётов
    op.create_index(
        "ix_orders_active_status",
        "orders",
        ["created_at"],
        unique=False,
        postgresql_where=sa.text("status NOT IN ('cancelled', 'completed')"),
    )

    # Индекс по нижнему регистру имени товара (для сортировки/поиска)
    op.create_index("ix_products_name_lower", "products", [sa.text("lower(name)")])

    # Индекс по цене со включением (covering index) — покрывает поиск без обращения к таблице
    op.create_index(
        "ix_products_price_covering",
        "products",
        ["price"],
        unique=False,
        postgresql_include={"id", "name", "slug", "stock"},
    )

    # Индекс по email для быстрого поиска (уже есть lower уникальный, добавим обычный)
    op.create_index("ix_users_email", "users", ["email"])

    # Индекс по дате создания заказа для аналитики
    op.create_index("ix_orders_created_at", "orders", ["created_at"])

    # ─────────────────────────────────────────────────────────────────
    # 13. Функция для обновления материализованного представления
    # ─────────────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE OR REPLACE FUNCTION refresh_popular_products()
        RETURNS TRIGGER AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY mv_popular_products;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
    )


def downgrade() -> None:
    # Сначала удаляем зависимые объекты (триггеры → функции → представления → таблицы)
    op.execute("DROP TRIGGER IF EXISTS trg_orders_status_change ON orders")
    op.execute("DROP TRIGGER IF EXISTS trg_users_admin_protect ON users")
    op.execute("DROP TRIGGER IF EXISTS trg_orders_status_validate ON orders")

    op.execute("DROP FUNCTION IF EXISTS refresh_popular_products()")
    op.execute("DROP FUNCTION IF EXISTS log_order_status_change()")
    op.execute("DROP FUNCTION IF EXISTS prevent_last_admin_deactivation()")
    op.execute("DROP FUNCTION IF EXISTS validate_order_status_transition()")
    op.execute("DROP FUNCTION IF EXISTS search_products_ranked(TEXT)")
    op.execute("DROP FUNCTION IF EXISTS get_popular_products(INTEGER)")
    op.execute("DROP FUNCTION IF EXISTS get_user_order_stats(UUID)")
    op.execute("DROP FUNCTION IF EXISTS get_dashboard_metrics()")
    op.execute("DROP FUNCTION IF EXISTS calculate_cart_total(UUID)")

    op.execute("DROP VIEW IF EXISTS vw_active_products")
    op.execute("DROP VIEW IF EXISTS vw_order_audit")
    op.execute("DROP VIEW IF EXISTS vw_user_order_summary")

    op.drop_index("ix_mv_popular_products_rank", table_name="mv_popular_products")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_popular_products")

    op.drop_index("ix_orders_pending_status", table_name="orders")
    op.drop_index("ix_orders_active_status", table_name="orders")
    op.drop_index("ix_products_name_lower", table_name="products")
    op.drop_index("ix_products_price_covering", table_name="products")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_orders_created_at", table_name="orders")

    op.drop_index("ix_order_status_log_changed_at", table_name="order_status_log")
    op.drop_index("ix_order_status_log_order_id", table_name="order_status_log")
    op.execute("DROP TABLE IF EXISTS order_status_log")
