import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listGroups, createGroup, updateGroup, deleteGroup } from "../api/groups";
import type { GroupWithCount } from "../api/types";

export function useGroups() {
  return useQuery({
    queryKey: ["groups"],
    queryFn: listGroups,
  });
}

export function useCreateGroup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; sort_order?: number }) => createGroup(data.name),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["groups"] }),
  });
}

export function useUpdateGroup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<GroupWithCount> }) =>
      updateGroup(id, data.name || ""),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["groups"] }),
  });
}

export function useDeleteGroup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteGroup(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["groups"] }),
  });
}
