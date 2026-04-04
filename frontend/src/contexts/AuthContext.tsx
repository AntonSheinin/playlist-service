import {
  useState,
  useEffect,
  useCallback,
  useRef,
  type ReactNode,
} from "react";
import { getMe, login as apiLogin, logout as apiLogout } from "../api/auth";
import type { LoginRequest } from "../api/types";
import { AuthContext, type AuthState } from "./auth-context";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    admin: null,
    loading: true,
  });
  const authRequestIdRef = useRef(0);

  useEffect(() => {
    const requestId = ++authRequestIdRef.current;
    let active = true;

    getMe()
      .then((admin) => {
        if (active && requestId === authRequestIdRef.current) {
          setState({ admin, loading: false });
        }
      })
      .catch(() => {
        if (active && requestId === authRequestIdRef.current) {
          setState({ admin: null, loading: false });
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(async (credentials: LoginRequest) => {
    authRequestIdRef.current += 1;
    await apiLogin(credentials);
    setState({ admin: null, loading: false });
  }, []);

  const logout = useCallback(async () => {
    authRequestIdRef.current += 1;
    try {
      await apiLogout();
    } catch {
      // Ignore errors; clear local state regardless.
    }
    setState({ admin: null, loading: false });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
