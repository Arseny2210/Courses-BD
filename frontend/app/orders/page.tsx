"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { useAuth } from "@/components/AuthProvider";
import { OrderStatusBadge } from "@/components/OrderStatusBadge";
import { apiRequest, formatDate, formatPrice } from "@/lib/api";
import { Order } from "@/lib/types";

export default function OrdersPage() {
  const { ready, token } = useAuth();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!ready) {
      return;
    }

    if (!token) {
      setLoading(false);
      return;
    }

    apiRequest<Order[]>("/api/orders", { token })
      .then(setOrders)
      .catch((error: Error) => setMessage(error.message))
      .finally(() => setLoading(false));
  }, [ready, token]);

  async function cancelOrder(orderId: string) {
    if (!token) {
      return;
    }

    try {
      const updatedOrder = await apiRequest<Order>(`/api/orders/${orderId}/cancel`, {
        method: "PATCH",
        token,
      });
      setOrders((current) => current.map((order) => (order.id === orderId ? updatedOrder : order)));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Не удалось отменить заказ");
    }
  }

  if (!ready) {
    return <div className="empty-state large">Проверяем сессию...</div>;
  }

  if (ready && !token) {
    return (
      <div className="empty-state large">
        <h1>Заказы доступны после входа</h1>
        <p>Авторизуйся, чтобы смотреть историю покупок и статус готовности.</p>
        <Link href="/login" className="primary-button link-button">
          Войти
        </Link>
      </div>
    );
  }

  return (
    <section className="panel">
      <div className="section-head">
        <div>
          <p className="eyebrow">Мои заказы</p>
          <h1>Статусы и готовность</h1>
        </div>
      </div>

      {message ? <p className="inline-message">{message}</p> : null}

      {loading ? (
        <div className="empty-state">Загружаем список заказов...</div>
      ) : orders.length === 0 ? (
        <div className="empty-state">
          <h2>Заказов пока нет</h2>
          <p>Сначала оформи заказ из корзины, и здесь появится его статус.</p>
        </div>
      ) : (
        <div className="orders-grid">
          {orders.map((order) => (
            <article key={order.id} className="order-card">
              <div className="order-card-head">
                <div>
                  <p className="muted">{order.order_number}</p>
                  <h2>{formatPrice(order.total_amount)}</h2>
                </div>
                <OrderStatusBadge status={order.status} />
              </div>

              <p className="muted">Создан: {formatDate(order.created_at)}</p>
              <p className="muted">Получатель: {order.recipient_name}</p>
              <p className="muted">Телефон: {order.customer_phone}</p>
              <p className="muted">Адрес: {order.delivery_address}</p>

              <div className="order-items-list">
                {order.items.map((item) => (
                  <div key={item.id} className="order-item-row">
                    <span>
                      {item.product_name} x {item.quantity}
                    </span>
                    <strong>{formatPrice(item.line_total)}</strong>
                  </div>
                ))}
              </div>

              {(order.status === "pending" || order.status === "processing") && (
                <button className="ghost-button" onClick={() => cancelOrder(order.id)}>
                  Отменить заказ
                </button>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
