"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import * as api from "../lib/api";
import type { AuthPayload, AuthUser, Billing } from "../lib/types";

interface AuthState {
  user: AuthUser | null;
  billing: Billing | null;
  loading: boolean;
  signup: (email: string, password: string, name: string) => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  guest: () => Promise<void>;
  orgSignup: (org: string, email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
  refreshBilling: () => Promise<void>;
}

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [billing, setBilling] = useState<Billing | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = api.getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .me()
      .then((r) => {
        setUser(r.user);
        setBilling(r.billing);
      })
      .catch(() => api.setToken(null))
      .finally(() => setLoading(false));
  }, []);

  const apply = useCallback((p: AuthPayload) => {
    api.setToken(p.token);
    setUser(p.user);
    setBilling(p.billing);
  }, []);

  const signup = useCallback(async (email: string, password: string, name: string) => {
    apply(await api.signup(email, password, name));
  }, [apply]);
  const login = useCallback(async (email: string, password: string) => {
    apply(await api.login(email, password));
  }, [apply]);
  const guest = useCallback(async () => {
    apply(await api.guest());
  }, [apply]);
  const orgSignup = useCallback(async (org: string, email: string, password: string, name: string) => {
    apply(await api.orgSignup(org, email, password, name));
  }, [apply]);

  const logout = useCallback(() => {
    api.setToken(null);
    setUser(null);
    setBilling(null);
  }, []);

  const refreshBilling = useCallback(async () => {
    try {
      setBilling(await api.getBilling());
    } catch {
      /* ignore */
    }
  }, []);

  return (
    <Ctx.Provider value={{ user, billing, loading, signup, login, guest, orgSignup, logout, refreshBilling }}>
      {children}
    </Ctx.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
