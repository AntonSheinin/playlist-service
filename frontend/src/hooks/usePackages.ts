import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listPackages,
  getPackage,
  createPackage,
  updatePackage,
  deletePackage,
  removeChannelFromPackage,
} from "../api/packages";

export function usePackages() {
  return useQuery({
    queryKey: ["packages"],
    queryFn: listPackages,
  });
}

export function usePackageDetail(id: number | undefined) {
  return useQuery({
    queryKey: ["packages", id],
    queryFn: () => getPackage(id!),
    enabled: !!id,
  });
}

export function useCreatePackage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; description?: string | null }) => createPackage(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["packages"] }),
  });
}

export function useUpdatePackage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: { name?: string; description?: string | null } }) =>
      updatePackage(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["packages"] }),
  });
}

export function useDeletePackage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deletePackage(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["packages"] }),
  });
}

export function useRemoveChannelFromPackage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ packageId, channelId }: { packageId: number; channelId: number }) =>
      removeChannelFromPackage(packageId, channelId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["packages"] }),
  });
}
