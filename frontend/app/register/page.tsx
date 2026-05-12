"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { useAuth } from "@/components/AuthProvider";

export default function RegisterPage() {
  const router = useRouter();
  const { register, user } = useAuth();
  const [form, setForm] = useState({ full_name: "", email: "", password: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (user) {
      router.push("/");
    }
  }, [router, user]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);

    try {
      await register(form);
      router.push("/");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Не удалось зарегистрироваться");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="auth-card">
      <div className="auth-intro">
        <p className="eyebrow">Регистрация</p>
        <h1>Создание аккаунта</h1>
        <p>Создай аккаунт, чтобы собирать корзину, оформлять заказы и отслеживать их статус.</p>
      </div>

      <form className="auth-form" onSubmit={handleSubmit}>
        <label>
          ФИО
          <input
            value={form.full_name}
            onChange={(event) => setForm((current) => ({ ...current, full_name: event.target.value }))}
            required
            minLength={2}
          />
        </label>

        <label>
          Email
          <input
            type="email"
            value={form.email}
            onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
            required
          />
        </label>

        <label>
          Пароль
          <input
            type="password"
            value={form.password}
            onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
            required
            minLength={6}
          />
        </label>

        {error ? <p className="form-error">{error}</p> : null}

        <button className="primary-button stretch" disabled={busy} type="submit">
          {busy ? "Создаём..." : "Создать аккаунт"}
        </button>

        <p className="form-note">
          Уже есть аккаунт? <Link href="/login">Войти</Link>
        </p>
      </form>
    </section>
  );
}
