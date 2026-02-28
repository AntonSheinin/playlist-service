import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listTariffs, createTariff, updateTariff, deleteTariff } from "../api/tariffs";
import { queryKeys } from "./queryKeys";

export function useTariffs() {
  return useQuery({
    queryKey: queryKeys.tariffs.all(),
    queryFn: listTariffs,
  });
}

export function useCreateTariff() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; description?: string | null; package_ids: number[] }) => createTariff(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.tariffs.all() });
      qc.invalidateQueries({ queryKey: queryKeys.lookup.tariffs() });
      qc.invalidateQueries({ queryKey: queryKeys.users.all() });
      qc.invalidateQueries({ queryKey: queryKeys.dashboard.stats() });
    },
  });
}

export function useUpdateTariff() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: { name?: string; description?: string | null; package_ids?: number[] } }) =>
      updateTariff(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.tariffs.all() });
      qc.invalidateQueries({ queryKey: queryKeys.lookup.tariffs() });
      qc.invalidateQueries({ queryKey: queryKeys.users.all() });
    },
  });
}

export function useDeleteTariff() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteTariff(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.tariffs.all() });
      qc.invalidateQueries({ queryKey: queryKeys.lookup.tariffs() });
      qc.invalidateQueries({ queryKey: queryKeys.users.all() });
      qc.invalidateQueries({ queryKey: queryKeys.dashboard.stats() });
    },
  });
}
