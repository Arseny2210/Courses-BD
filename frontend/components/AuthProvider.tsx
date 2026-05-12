"use client";

import {
  createContext,
  ReactNode,
  useContext,
  useEffect,
  useState,
} from "react";

import { apiRequest } from "@/lib/api";
import { clearStoredToken, getStoredToken, setStoredToken } from "@/lib/session";
import { AuthResponse, User } from "@/lib/types";

type LoginPayload = {
  email: string;
  password: string;
};

type RegisterPayload = LoginPayload & {
  full_name: string;
};

type AuthContextValue = {
  user: User | null;
  token: string | null;
  ready: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

async function fetchCurrentUser(token: string): Promise<User> {
  return apiRequest<User>("/api/auth/me", { token });
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const savedToken = getStoredToken();

    if (!savedToken) {
      setReady(true);
      return;
    }

    setToken(savedToken);
    fetchCurrentUser(savedToken)
      .then(setUser)
      .catch(() => {
        clearStoredToken();
        setToken(null);
        setUser(null);
      })
      .finally(() => setReady(true));
  }, []);

  async function handleAuthSuccess(response: AuthResponse) {
    setStoredToken(response.access_token);
    setToken(response.access_token);
    setUser(response.user);
  }

  async function login(payload: LoginPayload) {
    const response = await apiRequest<AuthResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    await handleAuthSuccess(response);
  }

  async function register(payload: RegisterPayload) {
    const response = await apiRequest<AuthResponse>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    await handleAuthSuccess(response);
  }

  function logout() {
    clearStoredToken();
    setToken(null);
    setUser(null);
  }

  async function refreshUser() {
    if (!token) {
      setUser(null);
      return;
    }

    const currentUser = await fetchCurrentUser(token);
    setUser(currentUser);
  }

  const value: AuthContextValue = {
    user,
    token,
    ready,
    login,
    register,
    logout,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
