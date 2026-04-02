import { fetchMessage, get } from "./client";
import type {
  AuthDashboardStats,
  DashboardStats,
  EpgDashboardStats,
  FlussonicDashboardStats,
  RutvDashboardStats,
} from "./types";

export function getStats(): Promise<DashboardStats> {
  return get<DashboardStats>("/api/v1/dashboard/stats");
}

export function getFlussonicStats(): Promise<FlussonicDashboardStats> {
  return get<FlussonicDashboardStats>("/api/v1/dashboard/flussonic");
}

export function getAuthStats(): Promise<AuthDashboardStats> {
  return get<AuthDashboardStats>("/api/v1/dashboard/auth");
}

export function getEpgStats(): Promise<EpgDashboardStats> {
  return get<EpgDashboardStats>("/api/v1/dashboard/epg");
}

export function getRutvStats(): Promise<RutvDashboardStats> {
  return get<RutvDashboardStats>("/api/v1/dashboard/rutv");
}

export function triggerEpgUpdate(): Promise<string> {
  return fetchMessage("/api/v1/dashboard/epg/update", { method: "POST" });
}
