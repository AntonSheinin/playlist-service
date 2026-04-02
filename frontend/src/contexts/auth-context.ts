import { createContext } from "react";
import type { AdminResponse, LoginRequest } from "../api/types";

export interface AuthState {
  admin: AdminResponse | null;
  loading: boolean;
}

export interface AuthContextValue extends AuthState {
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
