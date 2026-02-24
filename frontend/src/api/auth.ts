import { get, post } from "./client";
import type { AdminResponse, LoginRequest } from "./types";

export function login(data: LoginRequest): Promise<AdminResponse> {
  return post<AdminResponse>("/api/v1/auth/login", data);
}

export function logout(): Promise<void> {
  return post<void>("/api/v1/auth/logout");
}

export function getMe(): Promise<AdminResponse> {
  return get<AdminResponse>("/api/v1/auth/me");
}
