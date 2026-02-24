import { get, post, patch, fetchMessage } from "./client";
import type { GroupWithCount } from "./types";

export function listGroups(): Promise<GroupWithCount[]> {
  return get<GroupWithCount[]>("/api/v1/groups");
}

export function createGroup(name: string): Promise<GroupWithCount> {
  return post<GroupWithCount>("/api/v1/groups", { name });
}

export function updateGroup(id: number, name: string): Promise<GroupWithCount> {
  return patch<GroupWithCount>(`/api/v1/groups/${id}`, { name });
}

export function deleteGroup(id: number): Promise<string> {
  return fetchMessage(`/api/v1/groups/${id}`, { method: "DELETE" });
}
