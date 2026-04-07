import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getAuthStats,
  getEpgStats,
  getFlussonicStats,
  getNimbleStats,
  getRutvStats,
  getStats,
  triggerEpgUpdate,
} from "../api/dashboard";
import { queryKeys } from "./queryKeys";

const parsedServiceRefreshMs = Number(import.meta.env.VITE_SERVICE_DASHBOARD_REFRESH_MS);
const SERVICE_REFRESH_MS =
  Number.isFinite(parsedServiceRefreshMs) && parsedServiceRefreshMs > 0
    ? parsedServiceRefreshMs
    : false;

export function useDashboardStats() {
  return useQuery({
    queryKey: queryKeys.dashboard.stats(),
    queryFn: getStats,
  });
}

export function useFlussonicDashboardStats() {
  return useQuery({
    queryKey: queryKeys.dashboard.provider("flussonic"),
    queryFn: getFlussonicStats,
    refetchInterval: SERVICE_REFRESH_MS,
    refetchIntervalInBackground: true,
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
  });
}

export function useNimbleDashboardStats() {
  return useQuery({
    queryKey: queryKeys.dashboard.provider("nimble"),
    queryFn: getNimbleStats,
    refetchInterval: SERVICE_REFRESH_MS,
    refetchIntervalInBackground: true,
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
  });
}

export function useAuthDashboardStats() {
  return useQuery({
    queryKey: queryKeys.dashboard.auth(),
    queryFn: getAuthStats,
    refetchInterval: SERVICE_REFRESH_MS,
    refetchIntervalInBackground: true,
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
  });
}

export function useEpgDashboardStats() {
  return useQuery({
    queryKey: queryKeys.dashboard.epg(),
    queryFn: getEpgStats,
    refetchInterval: SERVICE_REFRESH_MS,
    refetchIntervalInBackground: true,
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
  });
}

export function useRutvDashboardStats() {
  return useQuery({
    queryKey: queryKeys.dashboard.rutv(),
    queryFn: getRutvStats,
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
      qc.invalidateQueries({ queryKey: queryKeys.dashboard.epg() });
    },
  });
}
