import { get, post, postVoid } from "./client";
import type { AdminResponse, LoginRequest } from "./types";

export function login(data: LoginRequest): Promise<void> {
  return postVoid("/api/v1/auth/login", data);
}

export function logout(): Promise<void> {
  return post<void>("/api/v1/auth/logout");
}

export function getMe(): Promise<AdminResponse> {
  return get<AdminResponse>("/api/v1/auth/me");
}
