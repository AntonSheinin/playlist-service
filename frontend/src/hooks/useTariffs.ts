import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listTariffs, createTariff, updateTariff, deleteTariff } from "../api/tariffs";

export function useTariffs() {
  return useQuery({
    queryKey: ["tariffs"],
    queryFn: listTariffs,
  });
}

export function useCreateTariff() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; description?: string | null; package_ids: number[] }) => createTariff(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tariffs"] }),
  });
}

export function useUpdateTariff() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: { name?: string; description?: string | null; package_ids?: number[] } }) =>
      updateTariff(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tariffs"] }),
  });
}

export function useDeleteTariff() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteTariff(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tariffs"] }),
  });
}
