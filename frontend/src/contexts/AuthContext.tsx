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

  const syncCurrentAdmin = useCallback(async (allowUnauthenticated = false) => {
    const requestId = ++authRequestIdRef.current;

    try {
      const admin = await getMe();
      if (requestId === authRequestIdRef.current) {
        setState({ admin, loading: false });
      }
      return admin;
    } catch (error) {
      if (requestId === authRequestIdRef.current) {
        setState({ admin: null, loading: false });
      }

      if (allowUnauthenticated) {
        return null;
      }

      throw error;
    }
  }, []);

  useEffect(() => {
    void syncCurrentAdmin(true);
  }, [syncCurrentAdmin]);

  const login = useCallback(async (credentials: LoginRequest) => {
    await apiLogin(credentials);
    await syncCurrentAdmin();
  }, [syncCurrentAdmin]);

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
