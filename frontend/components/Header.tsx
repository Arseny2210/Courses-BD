"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { useAuth } from "@/components/AuthProvider";

const NAV_ITEMS = [
  { href: "/", label: "Каталог" },
  { href: "/cart", label: "Корзина" },
  { href: "/orders", label: "Заказы" },
];

export function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();

  return (
    <header className="site-header">
      <div className="container header-inner">
        <Link href="/" className="brand">
          <span className="brand-mark">TS</span>
          <span>
            <strong>TechStore</strong>
            <small>Premium electronics store</small>
          </span>
        </Link>

        <nav className="nav">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={pathname === item.href ? "nav-link active" : "nav-link"}
            >
              {item.label}
            </Link>
          ))}
          {user?.is_admin ? (
            <Link
              href="/admin"
              className={pathname === "/admin" ? "nav-link active admin-link" : "nav-link admin-link"}
            >
              Панель
            </Link>
          ) : null}
        </nav>

        <div className="header-actions">
          {user ? (
            <>
              <div className="user-chip">
                <span>{user.full_name}</span>
                <small>{user.is_admin ? "Администратор" : "Покупатель"}</small>
              </div>
              <button
                className="ghost-button"
                onClick={() => {
                  logout();
                  router.push("/");
                }}
              >
                Выйти
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="ghost-button link-button">
                Вход
              </Link>
              <Link href="/register" className="primary-button link-button">
                Регистрация
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
