import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { setSessionExpiredHandler, tokenStore } from "../api/client";
import * as endpoints from "../api/endpoints";
import type { User } from "../api/types";

interface AuthState {
  user: User | null;
  /** true while the initial session restore is in flight */
  booting: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: {
    email: string;
    password: string;
    full_name: string;
    phone?: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [booting, setBooting] = useState(true);

  // Restore the session on page load if tokens exist.
  useEffect(() => {
    setSessionExpiredHandler(() => setUser(null));
    if (!tokenStore.access && !tokenStore.refresh) {
      setBooting(false);
      return;
    }
    endpoints
      .fetchMe()
      .then(setUser)
      .catch(() => tokenStore.clear())
      .finally(() => setBooting(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    tokenStore.set(await endpoints.login(email, password));
    setUser(await endpoints.fetchMe());
  }, []);

  const register = useCallback(
    async (data: { email: string; password: string; full_name: string; phone?: string }) => {
      await endpoints.register(data);
      // Auto-login after successful registration.
      tokenStore.set(await endpoints.login(data.email, data.password));
      setUser(await endpoints.fetchMe());
    },
    [],
  );

  const logout = useCallback(async () => {
    const refresh = tokenStore.refresh;
    if (refresh) {
      await endpoints.logout(refresh).catch(() => undefined);
    }
    tokenStore.clear();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, booting, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
