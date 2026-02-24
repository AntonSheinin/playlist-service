import { useQuery, useMutation, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import {
  listUsers,
  getUser,
  createUser,
  updateUser,
  deleteUser,
  regenerateToken,
  getResolvedChannels,
  previewPlaylist,
  getUserSessions,
  getUserAccessLogs,
} from "../api/users";
import type { UserCreate, UserUpdate } from "../api/types";

interface ListParams {
  page?: number;
  per_page?: number;
  sort_by?: string;
  sort_dir?: string;
  search?: string;
  status?: string;
  tariff_id?: number;
}

export function useUsers(params: ListParams) {
  return useQuery({
    queryKey: ["users", params],
    queryFn: () => listUsers(params),
    placeholderData: keepPreviousData,
  });
}

export function useUser(id: number | undefined) {
  return useQuery({
    queryKey: ["users", id],
    queryFn: () => getUser(id!),
    enabled: !!id,
  });
}

export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: UserCreate) => createUser(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });
}

export function useUpdateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UserUpdate }) => updateUser(id, data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["users", vars.id] });
      qc.invalidateQueries({ queryKey: ["users"] });
    },
  });
}

export function useDeleteUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteUser(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });
}

export function useRegenerateToken() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => regenerateToken(id),
    onSuccess: (_, id) => qc.invalidateQueries({ queryKey: ["users", id] }),
  });
}

export function useResolvedChannels(userId: number | undefined) {
  return useQuery({
    queryKey: ["users", userId, "channels"],
    queryFn: () => getResolvedChannels(userId!),
    enabled: !!userId,
  });
}

export function usePlaylistPreview(userId: number | undefined) {
  return useQuery({
    queryKey: ["users", userId, "playlist"],
    queryFn: () => previewPlaylist(userId!),
    enabled: !!userId,
  });
}

interface SessionParams {
  from_date?: string;
  to_date?: string;
}

export function useUserSessions(userId: number | undefined, params: SessionParams) {
  return useQuery({
    queryKey: ["users", userId, "sessions", params],
    queryFn: () => getUserSessions(userId!, params),
    enabled: !!userId,
  });
}

export function useUserAccessLogs(userId: number | undefined, params: SessionParams) {
  return useQuery({
    queryKey: ["users", userId, "access-logs", params],
    queryFn: () => getUserAccessLogs(userId!, params),
    enabled: !!userId,
  });
}
