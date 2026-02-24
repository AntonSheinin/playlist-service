import { useState } from "react";
import { Link } from "react-router-dom";
import { useDashboardStats } from "../hooks/useDashboard";
import { useSyncChannels } from "../hooks/useChannels";
import { useToast } from "../hooks/useToast";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "../components/ui/Button";
import { Spinner } from "../components/ui/Spinner";
import type { SyncResultResponse } from "../api/types";

export function DashboardPage() {
  const { data: stats, isLoading } = useDashboardStats();
  const syncMutation = useSyncChannels();
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const [syncResult, setSyncResult] = useState<SyncResultResponse | null>(null);

  async function handleSync() {
    try {
      const result = await syncMutation.mutateAsync();
      setSyncResult(result);
      showToast("Channels synchronized successfully", "success");
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
    } catch {
      showToast("Failed to sync channels", "error");
    }
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Dashboard</h1>

      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Channels */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0 bg-blue-100 rounded-md p-3">
              <svg className="h-6 w-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Channels</p>
              <p className="text-2xl font-semibold text-gray-900">{stats?.channels_total ?? "-"}</p>
              <p className="text-xs text-gray-500">
                {stats?.channels_synced ?? "-"} synced,{" "}
                <span className="text-orange-600">{stats?.channels_orphaned ?? "-"}</span> orphaned
              </p>
            </div>
          </div>
          <Link to="/channels" className="mt-4 block text-sm text-blue-600 hover:text-blue-800">
            View All &rarr;
          </Link>
        </div>

        {/* Groups */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0 bg-green-100 rounded-md p-3">
              <svg className="h-6 w-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Groups</p>
              <p className="text-2xl font-semibold text-gray-900">{stats?.groups ?? "-"}</p>
            </div>
          </div>
          <Link to="/groups" className="mt-4 block text-sm text-blue-600 hover:text-blue-800">
            View All &rarr;
          </Link>
        </div>

        {/* Packages & Tariffs */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0 bg-purple-100 rounded-md p-3">
              <svg className="h-6 w-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Packages / Tariffs</p>
              <p className="text-2xl font-semibold text-gray-900">
                {stats?.packages ?? "-"} / {stats?.tariffs ?? "-"}
              </p>
            </div>
          </div>
          <Link to="/packages" className="mt-4 block text-sm text-blue-600 hover:text-blue-800">
            View All &rarr;
          </Link>
        </div>

        {/* Users */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0 bg-yellow-100 rounded-md p-3">
              <svg className="h-6 w-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Users</p>
              <p className="text-2xl font-semibold text-gray-900">{stats?.users ?? "-"}</p>
              <p className="text-xs text-gray-500">
                <span className="text-green-600">{stats?.users_enabled ?? "-"}</span> enabled,{" "}
                <span className="text-red-600">{stats?.users_disabled ?? "-"}</span> disabled
              </p>
            </div>
          </div>
          <Link to="/users" className="mt-4 block text-sm text-blue-600 hover:text-blue-800">
            View All &rarr;
          </Link>
        </div>
      </div>

      {/* Flussonic Sync */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-800">Flussonic Sync</h2>
            <p className="text-sm text-gray-600 mt-1">
              Last sync:{" "}
              <span className="font-medium">
                {stats?.last_sync ? new Date(stats.last_sync).toLocaleString() : "Never"}
              </span>
            </p>
          </div>
          <Button onClick={handleSync} loading={syncMutation.isPending}>
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Sync from Flussonic
          </Button>
        </div>
        {syncResult && (
          <div className="mt-4">
            <div className="bg-green-50 border border-green-200 rounded-md p-4">
              <p className="text-sm text-green-800">
                Sync completed: {syncResult.total} total channels, {syncResult.new} new,{" "}
                {syncResult.updated} updated, {syncResult.orphaned} orphaned
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
