import { get, post, patch, fetchMessage } from "./client";
import type {
  UserListItem,
  UserResponse,
  UserCreate,
  UserUpdate,
  ResolvedChannel,
  PlaylistPreview,
  PaginatedData,
  SessionEntry,
  AccessLogEntry,
} from "./types";

interface ListUsersParams {
  page?: number;
  per_page?: number;
  search?: string;
  status?: string;
  tariff_id?: number;
  sort_by?: string;
  sort_dir?: string;
}

export function listUsers(
  params: ListUsersParams
): Promise<PaginatedData<UserListItem>> {
  const sp = new URLSearchParams();
  if (params.page) sp.set("page", String(params.page));
  if (params.per_page) sp.set("per_page", String(params.per_page));
  if (params.search) sp.set("search", params.search);
  if (params.status) sp.set("status", params.status);
  if (params.tariff_id) sp.set("tariff_id", String(params.tariff_id));
  if (params.sort_by) sp.set("sort_by", params.sort_by);
  if (params.sort_dir) sp.set("sort_dir", params.sort_dir);
  return get<PaginatedData<UserListItem>>(`/api/v1/users?${sp.toString()}`);
}

export function getUser(id: number): Promise<UserResponse> {
  return get<UserResponse>(`/api/v1/users/${id}`);
}

export function createUser(data: UserCreate): Promise<UserResponse> {
  return post<UserResponse>("/api/v1/users", data);
}

export function updateUser(
  id: number,
  data: UserUpdate
): Promise<UserResponse> {
  return patch<UserResponse>(`/api/v1/users/${id}`, data);
}

export function deleteUser(id: number): Promise<string> {
  return fetchMessage(`/api/v1/users/${id}`, { method: "DELETE" });
}

export function regenerateToken(id: number): Promise<UserResponse> {
  return post<UserResponse>(`/api/v1/users/${id}/regenerate-token`);
}

export function getResolvedChannels(id: number): Promise<ResolvedChannel[]> {
  return get<ResolvedChannel[]>(`/api/v1/users/${id}/resolved-channels`);
}

export function previewPlaylist(id: number): Promise<PlaylistPreview> {
  return get<PlaylistPreview>(`/api/v1/users/${id}/playlist/preview`);
}

interface LogParams {
  page?: number;
  per_page?: number;
  sort_by?: string;
  sort_dir?: string;
  from_date?: string;
  to_date?: string;
}

export function getUserSessions(
  userId: number,
  params: LogParams
): Promise<PaginatedData<SessionEntry>> {
  const sp = new URLSearchParams();
  if (params.page) sp.set("page", String(params.page));
  if (params.per_page) sp.set("per_page", String(params.per_page));
  if (params.sort_by) sp.set("sort_by", params.sort_by);
  if (params.sort_dir) sp.set("sort_dir", params.sort_dir);
  if (params.from_date) sp.set("from_date", params.from_date);
  if (params.to_date) sp.set("to_date", params.to_date);
  return get<PaginatedData<SessionEntry>>(`/api/v1/users/${userId}/sessions?${sp.toString()}`);
}

export function getUserAccessLogs(
  userId: number,
  params: LogParams
): Promise<PaginatedData<AccessLogEntry>> {
  const sp = new URLSearchParams();
  if (params.page) sp.set("page", String(params.page));
  if (params.per_page) sp.set("per_page", String(params.per_page));
  if (params.sort_by) sp.set("sort_by", params.sort_by);
  if (params.sort_dir) sp.set("sort_dir", params.sort_dir);
  if (params.from_date) sp.set("from_date", params.from_date);
  if (params.to_date) sp.set("to_date", params.to_date);
  return get<PaginatedData<AccessLogEntry>>(`/api/v1/users/${userId}/access-logs?${sp.toString()}`);
}
