import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, loginRequest, logoutRequest, restoreSession } from "../api/client";
import type { Role, User } from "../api/types";

interface AuthValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  reloadUser: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const reloadUser = useCallback(async () => {
    const me = await api<User>("/auth/me");
    setUser(me);
  }, []);

  const logout = useCallback(async () => {
    await logoutRequest();
    setUser(null);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    await loginRequest(email, password);
    await reloadUser();
  }, [reloadUser]);

  useEffect(() => {
    let active = true;
    const onExpired = () => setUser(null);
    window.addEventListener("biblioteca:session-expired", onExpired);
    void (async () => {
      try {
        if (await restoreSession()) {
          const restoredUser = await api<User>("/auth/me");
          if (active) setUser(restoredUser);
        }
      } catch {
        if (active) setUser(null);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
      window.removeEventListener("biblioteca:session-expired", onExpired);
    };
  }, [reloadUser]);

  const value = useMemo(() => ({ user, loading, login, logout, reloadUser }), [user, loading, login, logout, reloadUser]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth debe usarse dentro de AuthProvider");
  return context;
}

export function isStaff(role: Role | undefined): boolean {
  return role === "admin" || role === "bibliotecario";
}
