import {
  createContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { getMe, login as apiLogin, logout as apiLogout } from "../api/auth";
import type { AdminResponse, LoginRequest } from "../api/types";

interface AuthState {
  admin: AdminResponse | null;
  loading: boolean;
}

interface AuthContextValue extends AuthState {
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    admin: null,
    loading: true,
  });

  useEffect(() => {
    getMe()
      .then((admin) => setState({ admin, loading: false }))
      .catch(() => setState({ admin: null, loading: false }));
  }, []);

  const login = useCallback(async (credentials: LoginRequest) => {
    await apiLogin(credentials);
    const admin = await getMe();
    setState({ admin, loading: false });
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } catch {
      // Ignore errors — clear local state regardless
    }
    setState({ admin: null, loading: false });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
