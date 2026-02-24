import { get } from "./client";
import type { DashboardStats } from "./types";

export function getStats(): Promise<DashboardStats> {
  return get<DashboardStats>("/api/v1/dashboard/stats");
}
