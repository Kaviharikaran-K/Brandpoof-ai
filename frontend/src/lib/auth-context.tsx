"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { api, clearOrgId, currentOrgId, setCurrentOrgId } from "@/lib/api";
import type { Me, Role } from "@/lib/types";

interface AuthState {
  me: Me | null;
  loading: boolean;
  orgId: number | null;
  role: Role | null;
  setOrgId: (orgId: number) => void;
  refresh: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const [orgId, setOrgIdState] = useState<number | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await api<Me>("/api/auth/me");
      setMe(data);
      const stored = currentOrgId();
      const storedNum = stored ? Number(stored) : null;
      const valid =
        storedNum !== null && data.memberships.some((m) => m.org_id === storedNum)
          ? storedNum
          : data.memberships.length > 0
            ? data.memberships[0].org_id
            : null;
      if (valid !== null && valid !== storedNum) setCurrentOrgId(valid);
      setOrgIdState(valid);
    } catch {
      setMe(null);
      setOrgIdState(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const setOrgId = useCallback((id: number) => {
    setCurrentOrgId(id);
    setOrgIdState(id);
    void refresh();
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      await api("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      setLoading(true);
      await refresh();
    },
    [refresh]
  );

  const register = useCallback(
    async (email: string, password: string, fullName: string) => {
      await api("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password, full_name: fullName }),
      });
      setLoading(true);
      await refresh();
    },
    [refresh]
  );

  const logout = useCallback(async () => {
    try {
      await api("/api/auth/logout", { method: "POST" });
    } finally {
      clearOrgId();
      setMe(null);
      setOrgIdState(null);
    }
  }, []);

  const membership = me?.memberships.find((m) => m.org_id === orgId) ?? null;
  const role = membership?.role ?? null;

  return (
    <AuthContext.Provider
      value={{ me, loading, orgId, role, setOrgId, refresh, login, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
