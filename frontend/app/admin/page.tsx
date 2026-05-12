"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";

import { useAuth } from "@/components/AuthProvider";
import { OrderStatusBadge } from "@/components/OrderStatusBadge";
import { ORDER_STATUS_LABELS, apiRequest, formatDate, formatPrice } from "@/lib/api";
import { Order, OrderStatus, Product } from "@/lib/types";

const EMPTY_PRODUCT_FORM = {
  name: "",
  slug: "",
  description: "",
  price: "0",
  stock: 0,
  image_url: "",
  is_active: true,
};

export default function AdminPage() {
  const { ready, token, user } = useAuth();
  const [products, setProducts] = useState<Product[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [form, setForm] = useState(EMPTY_PRODUCT_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!ready) {
      return;
    }

    if (!token || !user?.is_admin) {
      setLoading(false);
      return;
    }

    Promise.all([
      apiRequest<Product[]>("/api/admin/products", { token }),
      apiRequest<Order[]>("/api/admin/orders", { token }),
    ])
      .then(([productsResponse, ordersResponse]) => {
        setProducts(productsResponse);
        setOrders(ordersResponse);
      })
      .catch((error: Error) => setMessage(error.message))
      .finally(() => setLoading(false));
  }, [ready, token, user?.is_admin]);

  function resetForm() {
    setEditingId(null);
    setForm(EMPTY_PRODUCT_FORM);
  }

  async function reloadProducts() {
    if (!token) {
      return;
    }
    const response = await apiRequest<Product[]>("/api/admin/products", { token });
    setProducts(response);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) {
      return;
    }

    setBusy(true);
    setMessage(null);

    const payload = {
      ...form,
      slug: form.slug || null,
      image_url: form.image_url || null,
      price: Number(form.price),
    };

    try {
      if (editingId) {
        await apiRequest(`/api/admin/products/${editingId}`, {
          method: "PATCH",
          token,
          body: JSON.stringify(payload),
        });
      } else {
        await apiRequest("/api/admin/products", {
          method: "POST",
          token,
          body: JSON.stringify(payload),
        });
      }

      await reloadProducts();
      resetForm();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Не удалось сохранить товар");
    } finally {
      setBusy(false);
    }
  }

  async function removeProduct(productId: string) {
    if (!token) {
      return;
    }

    setBusy(true);
    try {
      await apiRequest(`/api/admin/products/${productId}`, {
        method: "DELETE",
        token,
      });
      await reloadProducts();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Не удалось удалить товар");
    } finally {
      setBusy(false);
    }
  }

  async function updateOrderStatus(orderId: string, status: OrderStatus) {
    if (!token) {
      return;
    }

    try {
      const updatedOrder = await apiRequest<Order>(`/api/admin/orders/${orderId}`, {
        method: "PATCH",
        token,
        body: JSON.stringify({ status }),
      });
      setOrders((current) => current.map((order) => (order.id === orderId ? updatedOrder : order)));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Не удалось обновить статус заказа");
    }
  }

  if (!ready) {
    return <div className="empty-state large">Проверяем доступ администратора...</div>;
  }

  if (ready && !token) {
    return (
      <div className="empty-state large">
        <h1>Панель управления доступна после входа</h1>
        <p>Войди под администратором, чтобы управлять каталогом, остатками и заказами.</p>
        <Link href="/login" className="primary-button link-button">
          Перейти ко входу
        </Link>
      </div>
    );
  }

  if (ready && user && !user.is_admin) {
    return (
      <div className="empty-state large">
        <h1>Недостаточно прав</h1>
        <p>Эта страница доступна только сотрудникам, которые управляют каталогом и заказами.</p>
      </div>
    );
  }

  return (
    <div className="page-stack">
      <section className="panel">
        <div className="section-head">
          <div>
            <p className="eyebrow">Панель управления</p>
            <h1>Управление каталогом</h1>
          </div>
        </div>

        {message ? <p className="inline-message">{message}</p> : null}

        <form className="grid-form" onSubmit={handleSubmit}>
          <label>
            Название
            <input
              value={form.name}
              onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
              required
            />
          </label>

          <label>
            Slug
            <input
              value={form.slug}
              onChange={(event) => setForm((current) => ({ ...current, slug: event.target.value }))}
              placeholder="Можно оставить пустым"
            />
          </label>

          <label>
            Цена
            <input
              type="number"
              min={0}
              step="0.01"
              value={form.price}
              onChange={(event) => setForm((current) => ({ ...current, price: event.target.value }))}
              required
            />
          </label>

          <label>
            Остаток
            <input
              type="number"
              min={0}
              value={form.stock}
              onChange={(event) =>
                setForm((current) => ({ ...current, stock: Number(event.target.value) }))
              }
              required
            />
          </label>

          <label className="full-width">
            Ссылка на изображение
            <input
              value={form.image_url}
              onChange={(event) => setForm((current) => ({ ...current, image_url: event.target.value }))}
            />
          </label>

          <label className="full-width">
            Описание
            <textarea
              rows={4}
              value={form.description}
              onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
              required
            />
          </label>

          <label className="toggle-label">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(event) => setForm((current) => ({ ...current, is_active: event.target.checked }))}
            />
            Товар активен и виден в каталоге
          </label>

          <div className="button-row">
            <button className="primary-button" disabled={busy} type="submit">
              {editingId ? "Сохранить изменения" : "Создать товар"}
            </button>
            {editingId ? (
              <button className="ghost-button" type="button" onClick={resetForm}>
                Отменить редактирование
              </button>
            ) : null}
          </div>
        </form>

        {loading ? (
          <div className="empty-state">Загружаем данные панели управления...</div>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Товар</th>
                  <th>Цена</th>
                  <th>Склад</th>
                  <th>Статус</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {products.map((product) => (
                  <tr key={product.id}>
                    <td>
                      <strong>{product.name}</strong>
                      <div className="table-note">{product.slug}</div>
                    </td>
                    <td>{formatPrice(product.price)}</td>
                    <td>{product.stock}</td>
                    <td>{product.is_active ? "Активен" : "Скрыт"}</td>
                    <td className="table-actions">
                      <button
                        className="ghost-button"
                        onClick={() => {
                          setEditingId(product.id);
                          setForm({
                            name: product.name,
                            slug: product.slug ?? "",
                            description: product.description,
                            price: String(product.price),
                            stock: product.stock,
                            image_url: product.image_url ?? "",
                            is_active: product.is_active,
                          });
                        }}
                      >
                        Изменить
                      </button>
                      <button className="ghost-button danger-text" onClick={() => removeProduct(product.id)}>
                        Удалить
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel">
        <div className="section-head">
          <div>
            <p className="eyebrow">Заказы</p>
            <h2>Смена статусов</h2>
          </div>
        </div>

        <div className="orders-grid">
          {orders.length === 0 ? (
            <div className="empty-state">Пока нет заказов для обработки.</div>
          ) : (
            orders.map((order) => (
              <article key={order.id} className="order-card">
                <div className="order-card-head">
                  <div>
                    <p className="muted">{order.order_number}</p>
                    <h3>{order.recipient_name}</h3>
                  </div>
                  <OrderStatusBadge status={order.status} />
                </div>

                <p className="muted">Создан: {formatDate(order.created_at)}</p>
                <p className="muted">Телефон: {order.customer_phone}</p>
                <p className="muted">Адрес: {order.delivery_address}</p>
                <p className="muted">Сумма: {formatPrice(order.total_amount)}</p>

                <select
                  className="status-select"
                  value={order.status}
                  onChange={(event) => updateOrderStatus(order.id, event.target.value as OrderStatus)}
                >
                  {Object.entries(ORDER_STATUS_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </article>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
