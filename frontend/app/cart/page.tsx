"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { useAuth } from "@/components/AuthProvider";
import { apiRequest, formatPrice } from "@/lib/api";
import { Cart } from "@/lib/types";

const EMPTY_ORDER_FORM = {
  recipient_name: "",
  delivery_address: "",
  customer_phone: "",
  comment: "",
};

export default function CartPage() {
  const router = useRouter();
  const { ready, token, user } = useAuth();
  const [cart, setCart] = useState<Cart | null>(null);
  const [orderForm, setOrderForm] = useState(EMPTY_ORDER_FORM);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (user?.full_name) {
      setOrderForm((current) => ({ ...current, recipient_name: current.recipient_name || user.full_name }));
    }
  }, [user?.full_name]);

  useEffect(() => {
    if (!ready) {
      return;
    }

    if (!token) {
      return;
    }

    apiRequest<Cart>("/api/cart", { token })
      .then(setCart)
      .catch((error: Error) => setMessage(error.message));
  }, [ready, token]);

  async function reloadCart() {
    if (!token) {
      return;
    }

    const response = await apiRequest<Cart>("/api/cart", { token });
    setCart(response);
  }

  async function changeQuantity(itemId: string, quantity: number) {
    if (!token) {
      return;
    }

    setBusy(true);
    setMessage(null);
    try {
      const response = await apiRequest<Cart>(`/api/cart/items/${itemId}`, {
        method: "PATCH",
        token,
        body: JSON.stringify({ quantity }),
      });
      setCart(response);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Не удалось обновить количество");
    } finally {
      setBusy(false);
    }
  }

  async function removeItem(itemId: string) {
    if (!token) {
      return;
    }

    setBusy(true);
    try {
      const response = await apiRequest<Cart>(`/api/cart/items/${itemId}`, {
        method: "DELETE",
        token,
      });
      setCart(response);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Не удалось удалить товар");
    } finally {
      setBusy(false);
    }
  }

  async function clearCart() {
    if (!token) {
      return;
    }

    setBusy(true);
    try {
      const response = await apiRequest<Cart>("/api/cart", {
        method: "DELETE",
        token,
      });
      setCart(response);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Не удалось очистить корзину");
    } finally {
      setBusy(false);
    }
  }

  async function handleCheckout(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) {
      return;
    }

    setBusy(true);
    setMessage(null);
    try {
      await apiRequest("/api/orders", {
        method: "POST",
        token,
        body: JSON.stringify({
          ...orderForm,
          comment: orderForm.comment || null,
        }),
      });
      setOrderForm((current) => ({ ...current, delivery_address: "", customer_phone: "", comment: "" }));
      await reloadCart();
      router.push("/orders");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Не удалось оформить заказ");
    } finally {
      setBusy(false);
    }
  }

  if (!ready) {
    return <div className="empty-state large">Проверяем сессию...</div>;
  }

  if (ready && !token) {
    return (
      <div className="empty-state large">
        <h1>Корзина доступна после входа</h1>
        <p>Сначала авторизуйся, и тогда можно будет добавлять технику и оформлять заказ.</p>
        <Link href="/login" className="primary-button link-button">
          Перейти ко входу
        </Link>
      </div>
    );
  }

  return (
    <div className="page-stack">
      <section className="panel">
        <div className="section-head">
          <div>
            <p className="eyebrow">Корзина</p>
            <h1>Текущие товары</h1>
          </div>
          <button className="ghost-button" disabled={busy || !cart?.items.length} onClick={clearCart}>
            Очистить корзину
          </button>
        </div>

        {message ? <p className="inline-message">{message}</p> : null}

        {!cart ? (
          <div className="empty-state">Загружаем корзину...</div>
        ) : cart.items.length === 0 ? (
          <div className="empty-state">
            <h2>Корзина пока пустая</h2>
            <p>Выбери товар в каталоге и вернись сюда для оформления заказа.</p>
            <Link href="/" className="primary-button link-button">
              В каталог
            </Link>
          </div>
        ) : (
          <div className="cart-layout">
            <div className="cart-items">
              {cart.items.map((item) => (
                <article key={item.id} className="cart-item-card">
                  <div>
                    <h3>{item.product_name}</h3>
                    <p className="muted">{formatPrice(item.product_price)} за штуку</p>
                    <p className="muted">На складе: {item.stock}</p>
                  </div>

                  <div className="cart-item-controls">
                    <label>
                      Количество
                      <input
                        type="number"
                        min={1}
                        max={item.stock}
                        value={item.quantity}
                        onChange={(event) => {
                          const nextQuantity = Number(event.target.value);
                          if (Number.isInteger(nextQuantity) && nextQuantity >= 1) {
                            changeQuantity(item.id, nextQuantity);
                          }
                        }}
                      />
                    </label>
                    <strong>{formatPrice(item.line_total)}</strong>
                    <button className="ghost-button" disabled={busy} onClick={() => removeItem(item.id)}>
                      Удалить
                    </button>
                  </div>
                </article>
              ))}
            </div>

            <aside className="summary-card">
              <p className="eyebrow">Итог</p>
              <h2>{formatPrice(cart.total_amount)}</h2>
              <p>{cart.total_items} товаров в корзине</p>
            </aside>
          </div>
        )}
      </section>

      <section className="panel">
        <div className="section-head">
          <div>
            <p className="eyebrow">Оформление</p>
            <h2>Создать заказ</h2>
          </div>
        </div>

        <form className="grid-form" onSubmit={handleCheckout}>
          <label>
            Получатель
            <input
              value={orderForm.recipient_name}
              onChange={(event) =>
                setOrderForm((current) => ({ ...current, recipient_name: event.target.value }))
              }
              required
            />
          </label>

          <label>
            Телефон
            <input
              value={orderForm.customer_phone}
              onChange={(event) =>
                setOrderForm((current) => ({ ...current, customer_phone: event.target.value }))
              }
              required
            />
          </label>

          <label className="full-width">
            Адрес / место выдачи
            <textarea
              value={orderForm.delivery_address}
              onChange={(event) =>
                setOrderForm((current) => ({ ...current, delivery_address: event.target.value }))
              }
              required
              rows={4}
            />
          </label>

          <label className="full-width">
            Комментарий
            <textarea
              value={orderForm.comment}
              onChange={(event) => setOrderForm((current) => ({ ...current, comment: event.target.value }))}
              rows={3}
            />
          </label>

          <button className="primary-button" disabled={busy || !cart?.items.length} type="submit">
            {busy ? "Оформляем..." : "Оформить заказ"}
          </button>
        </form>
      </section>
    </div>
  );
}
