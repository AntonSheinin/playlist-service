import { useQuery, useMutation, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import {
  listChannels,
  updateChannel,
  bulkUpdateChannels,
  deleteChannel,
  updateChannelGroups,
  updateChannelPackages,
  syncChannels,
  getCascadeInfo,
  uploadLogo,
  uploadLogoByUrl,
  removeLogo,
} from "../api/channels";
import type { ChannelBulkUpdateItem } from "../api/types";
import { queryKeys } from "./queryKeys";

interface ListParams {
  page?: number;
  per_page?: number;
  sort_by?: string;
  sort_dir?: string;
  search?: string;
  group_id?: number;
  sync_status?: string;
}

export function useChannels(params: ListParams) {
  return useQuery({
    queryKey: queryKeys.channels.list(params),
    queryFn: () => listChannels(params),
    placeholderData: keepPreviousData,
  });
}

export function useUpdateChannel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Record<string, unknown> }) =>
      updateChannel(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.channels.all() });
      qc.invalidateQueries({ queryKey: queryKeys.lookup.channels() });
    },
  });
}

export function useBulkUpdateChannels() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (items: ChannelBulkUpdateItem[]) => bulkUpdateChannels(items),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.channels.all() });
      qc.invalidateQueries({ queryKey: queryKeys.lookup.channels() });
    },
  });
}

export function useDeleteChannel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, force }: { id: number; force?: boolean }) =>
      deleteChannel(id, force),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.channels.all() });
      qc.invalidateQueries({ queryKey: queryKeys.lookup.channels() });
      qc.invalidateQueries({ queryKey: queryKeys.packages.all() });
      qc.invalidateQueries({ queryKey: queryKeys.users.all() });
      qc.invalidateQueries({ queryKey: queryKeys.dashboard.stats() });
    },
  });
}

export function useUpdateChannelGroups() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, groupIds }: { id: number; groupIds: number[] }) =>
      updateChannelGroups(id, groupIds),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.channels.all() });
      qc.invalidateQueries({ queryKey: queryKeys.groups.all() });
      qc.invalidateQueries({ queryKey: queryKeys.lookup.groups() });
    },
  });
}

export function useUpdateChannelPackages() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, packageIds }: { id: number; packageIds: number[] }) =>
      updateChannelPackages(id, packageIds),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.channels.all() });
      qc.invalidateQueries({ queryKey: queryKeys.packages.all() });
      qc.invalidateQueries({ queryKey: queryKeys.users.all() });
    },
  });
}

export function useSyncChannels() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => syncChannels(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.channels.all() });
      qc.invalidateQueries({ queryKey: queryKeys.lookup.channels() });
      qc.invalidateQueries({ queryKey: queryKeys.dashboard.stats() });
    },
  });
}

export function useCascadeInfo(channelId: number | null) {
  return useQuery({
    queryKey: queryKeys.channels.cascade(channelId),
    queryFn: () => getCascadeInfo(channelId!),
    enabled: channelId !== null,
  });
}

export function useUploadLogo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, file }: { id: number; file: File }) => uploadLogo(id, file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.channels.all() });
      qc.invalidateQueries({ queryKey: queryKeys.lookup.channels() });
    },
  });
}

export function useUploadLogoByUrl() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, url }: { id: number; url: string }) => uploadLogoByUrl(id, url),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.channels.all() });
      qc.invalidateQueries({ queryKey: queryKeys.lookup.channels() });
    },
  });
}

export function useRemoveLogo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, deleteFile }: { id: number; deleteFile: boolean }) => removeLogo(id, deleteFile),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.channels.all() });
      qc.invalidateQueries({ queryKey: queryKeys.lookup.channels() });
    },
  });
}
