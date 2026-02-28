import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getAuthStats, getEpgStats, getFlussonicStats, getStats, triggerEpgUpdate } from "../api/dashboard";

const parsedServiceRefreshMs = Number(import.meta.env.VITE_FLUSSONIC_DASHBOARD_REFRESH_MS);
const SERVICE_REFRESH_MS =
  Number.isFinite(parsedServiceRefreshMs) && parsedServiceRefreshMs > 0
    ? parsedServiceRefreshMs
    : false;

export function useDashboardStats() {
  return useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: getStats,
  });
}

export function useFlussonicDashboardStats() {
  return useQuery({
    queryKey: ["dashboard-flussonic-stats"],
    queryFn: getFlussonicStats,
    refetchInterval: SERVICE_REFRESH_MS,
    refetchIntervalInBackground: true,
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
  });
}

export function useAuthDashboardStats() {
  return useQuery({
    queryKey: ["dashboard-auth-stats"],
    queryFn: getAuthStats,
    refetchInterval: SERVICE_REFRESH_MS,
    refetchIntervalInBackground: true,
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
  });
}

export function useEpgDashboardStats() {
  return useQuery({
    queryKey: ["dashboard-epg-stats"],
    queryFn: getEpgStats,
    refetchInterval: SERVICE_REFRESH_MS,
    refetchIntervalInBackground: true,
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
  });
}

export function useTriggerEpgUpdate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => triggerEpgUpdate(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["dashboard-epg-stats"] });
    },
  });
}
