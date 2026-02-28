import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listPackages,
  getPackage,
  createPackage,
  updatePackage,
  deletePackage,
  removeChannelFromPackage,
} from "../api/packages";
import { queryKeys } from "./queryKeys";

export function usePackages() {
  return useQuery({
    queryKey: queryKeys.packages.all(),
    queryFn: listPackages,
  });
}

export function usePackageDetail(id: number | undefined) {
  return useQuery({
    queryKey: queryKeys.packages.detail(id),
    queryFn: () => getPackage(id!),
    enabled: !!id,
  });
}

export function useCreatePackage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; description?: string | null }) => createPackage(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.packages.all() });
      qc.invalidateQueries({ queryKey: queryKeys.lookup.packages() });
      qc.invalidateQueries({ queryKey: queryKeys.dashboard.stats() });
    },
  });
}

export function useUpdatePackage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: { name?: string; description?: string | null } }) =>
      updatePackage(id, data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: queryKeys.packages.all() });
      qc.invalidateQueries({ queryKey: queryKeys.packages.detail(vars.id) });
      qc.invalidateQueries({ queryKey: queryKeys.lookup.packages() });
      qc.invalidateQueries({ queryKey: queryKeys.tariffs.all() });
      qc.invalidateQueries({ queryKey: queryKeys.users.all() });
      qc.invalidateQueries({ queryKey: queryKeys.channels.all() });
    },
  });
}

export function useDeletePackage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deletePackage(id),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: queryKeys.packages.all() });
      qc.invalidateQueries({ queryKey: queryKeys.packages.detail(id) });
      qc.invalidateQueries({ queryKey: queryKeys.lookup.packages() });
      qc.invalidateQueries({ queryKey: queryKeys.tariffs.all() });
      qc.invalidateQueries({ queryKey: queryKeys.users.all() });
      qc.invalidateQueries({ queryKey: queryKeys.channels.all() });
      qc.invalidateQueries({ queryKey: queryKeys.dashboard.stats() });
    },
  });
}

export function useRemoveChannelFromPackage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ packageId, channelId }: { packageId: number; channelId: number }) =>
      removeChannelFromPackage(packageId, channelId),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: queryKeys.packages.all() });
      qc.invalidateQueries({ queryKey: queryKeys.packages.detail(vars.packageId) });
      qc.invalidateQueries({ queryKey: queryKeys.channels.all() });
      qc.invalidateQueries({ queryKey: queryKeys.users.all() });
    },
  });
}
