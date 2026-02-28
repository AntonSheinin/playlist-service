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
import { queryKeys } from "./queryKeys";

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
    queryKey: queryKeys.users.list(params),
    queryFn: () => listUsers(params),
    placeholderData: keepPreviousData,
  });
}

export function useUser(id: number | undefined) {
  return useQuery({
    queryKey: queryKeys.users.detail(id),
    queryFn: () => getUser(id!),
    enabled: !!id,
  });
}

export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: UserCreate) => createUser(data),
    onSuccess: (created) => {
      qc.invalidateQueries({ queryKey: queryKeys.users.all() });
      qc.invalidateQueries({ queryKey: queryKeys.users.detail(created.id) });
      qc.invalidateQueries({ queryKey: queryKeys.dashboard.stats() });
    },
  });
}

export function useUpdateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UserUpdate }) => updateUser(id, data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: queryKeys.users.detail(vars.id) });
      qc.invalidateQueries({ queryKey: queryKeys.users.resolvedChannels(vars.id) });
      qc.invalidateQueries({ queryKey: queryKeys.users.playlist(vars.id) });
      qc.invalidateQueries({ queryKey: queryKeys.users.all() });
      qc.invalidateQueries({ queryKey: queryKeys.dashboard.stats() });
    },
  });
}

export function useDeleteUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteUser(id),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: queryKeys.users.detail(id) });
      qc.invalidateQueries({ queryKey: queryKeys.users.resolvedChannels(id) });
      qc.invalidateQueries({ queryKey: queryKeys.users.playlist(id) });
      qc.invalidateQueries({ queryKey: queryKeys.users.all() });
      qc.invalidateQueries({ queryKey: queryKeys.dashboard.stats() });
    },
  });
}

export function useRegenerateToken() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => regenerateToken(id),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: queryKeys.users.detail(id) });
      qc.invalidateQueries({ queryKey: queryKeys.users.playlist(id) });
    },
  });
}

export function useResolvedChannels(userId: number | undefined) {
  return useQuery({
    queryKey: queryKeys.users.resolvedChannels(userId),
    queryFn: () => getResolvedChannels(userId!),
    enabled: !!userId,
  });
}

export function usePlaylistPreview(userId: number | undefined) {
  return useQuery({
    queryKey: queryKeys.users.playlist(userId),
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
    queryKey: queryKeys.users.sessions(userId, params),
    queryFn: () => getUserSessions(userId!, params),
    enabled: !!userId,
  });
}

export function useUserAccessLogs(userId: number | undefined, params: SessionParams) {
  return useQuery({
    queryKey: queryKeys.users.accessLogs(userId, params),
    queryFn: () => getUserAccessLogs(userId!, params),
    enabled: !!userId,
  });
}
