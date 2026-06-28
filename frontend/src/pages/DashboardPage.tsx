import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  useAuthDashboardStats,
  useDashboardStats,
  useEpgDashboardStats,
  useFlussonicDashboardStats,
  useNimbleDashboardStats,
  useRutvDashboardStats,
  useTriggerEpgUpdate,
} from "../hooks/useDashboard";
import { useSyncChannels } from "../hooks/useChannels";
import { useToast } from "../hooks/useToast";
import { Button } from "../components/ui/Button";
import { Spinner } from "../components/ui/Spinner";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { PageHeader } from "../components/ui/PageHeader";
import { SectionCard } from "../components/ui/SectionCard";
import type { StreamSource } from "../api/types";
import { formatStreamSource } from "../utils/channels";

function StatCard({
  iconBg,
  icon,
  title,
  value,
  meta,
  linkTo,
}: {
  iconBg: string;
  icon: ReactNode;
  title: string;
  value: string | number;
  meta?: ReactNode;
  linkTo: string;
}) {
  return (
    <Card className="p-5">
      <div className="flex items-start gap-4">
        <div className={`rounded-lg p-3 ${iconBg}`}>
          {icon}
        </div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-muted-foreground">{title}</p>
          <p className="text-2xl font-semibold text-card-foreground">{value}</p>
          {meta && <div className="mt-1 text-xs text-muted-foreground">{meta}</div>}
        </div>
      </div>
      <Link to={linkTo} className="mt-4 block text-sm font-medium text-accent-foreground hover:brightness-90">
        View All &rarr;
      </Link>
    </Card>
  );
}

function formatTrafficKbit(value: number | null | undefined): string {
  if (value === null || value === undefined) return "N/A";
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)} Gbit/s`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(2)} Mbit/s`;
  return `${value} Kbit/s`;
}

function formatDateTime(value: string | null | undefined): string {
  return value ? new Date(value).toLocaleString() : "N/A";
}

function isNotConfigured(error: string | null | undefined): boolean {
  return error === "Not configured";
}

function getHealthBadgeVariant(
  health: "up" | "degraded" | "down" | undefined,
  error?: string | null
): "green" | "yellow" | "red" | "gray" {
  if (isNotConfigured(error)) return "gray";
  if (health === "up") return "green";
  if (health === "degraded") return "yellow";
  if (health === "down") return "red";
  return "gray";
}

export function DashboardPage() {
  const { data: stats, isLoading } = useDashboardStats();
  const { data: flussonicStats, isLoading: isFlussonicLoading } = useFlussonicDashboardStats();
  const { data: nimbleStats, isLoading: isNimbleLoading } = useNimbleDashboardStats();
  const { data: authStats, isLoading: isAuthLoading } = useAuthDashboardStats();
  const { data: epgStats, isLoading: isEpgLoading } = useEpgDashboardStats();
  const { data: rutvStats, isLoading: isRutvLoading } = useRutvDashboardStats();
  const epgUpdateMutation = useTriggerEpgUpdate();
  const syncMutation = useSyncChannels();
  const { showToast } = useToast();
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  async function handleSync(source: StreamSource) {
    try {
      const result = await syncMutation.mutateAsync(source);
      const message = `${formatStreamSource(result.source)} sync completed: ${result.total} total, ${result.new} new, ${result.updated} updated, ${result.orphaned} orphaned`;
      setSyncMessage(message);
      showToast(message, "success");
    } catch {
      showToast("Failed to sync channels", "error");
    }
  }

  async function handleEpgUpdate() {
    try {
      const message = await epgUpdateMutation.mutateAsync();
      showToast(message || "EPG update completed", "success");
    } catch {
      showToast("Failed to trigger EPG update", "error");
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
      <PageHeader title="Dashboard" description="Overview of channels, groups, packages, tariffs, and users." />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          iconBg="status-info"
          linkTo="/channels"
          title="Channels"
          value={stats?.channels_total ?? "-"}
          meta={
            <>
              {stats?.channels_synced ?? "-"} synced,{" "}
              <span className="text-[var(--status-warning-text)]">{stats?.channels_orphaned ?? "-"}</span> orphaned
            </>
          }
          icon={
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          }
        />
        <StatCard
          iconBg="status-success"
          linkTo="/groups"
          title="Groups"
          value={stats?.groups ?? "-"}
          icon={
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
          }
        />
        <StatCard
          iconBg="status-neutral"
          linkTo="/packages"
          title="Packages / Tariffs"
          value={`${stats?.packages ?? "-"} / ${stats?.tariffs ?? "-"}`}
          icon={
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
            </svg>
          }
        />
        <StatCard
          iconBg="status-warning"
          linkTo="/users"
          title="Users"
          value={stats?.users ?? "-"}
          meta={
            <>
              <span className="text-[var(--status-success-text)]">{stats?.users_enabled ?? "-"}</span> enabled,{" "}
              <span className="text-[var(--status-danger-text)]">{stats?.users_disabled ?? "-"}</span> disabled
            </>
          }
          icon={
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          }
        />
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
        <SectionCard
          className="xl:col-span-1"
          title={(
            <div className="flex items-center gap-2">
              <Badge variant={getHealthBadgeVariant(epgStats?.health)}>
                {epgStats?.health?.toUpperCase() ?? (isEpgLoading ? "LOADING" : "N/A")}
              </Badge>
              <span>EPG Service</span>
            </div>
          )}
          bodyClassName="flex flex-col gap-4"
          actions={
            <Button onClick={handleEpgUpdate} loading={epgUpdateMutation.isPending}>
              <svg className="mr-2 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Fetch Now
            </Button>
          }
        >
          <div className="w-full rounded-xl border border-border bg-muted p-4">
            <div className="flex flex-col">
              <div className="space-y-2 text-sm text-muted-foreground">
                <p>
                  Last fetch:{" "}
                  <span className="font-semibold text-foreground">{formatDateTime(epgStats?.last_epg_update_at)}</span>
                </p>
                <p>
                  Next fetch:{" "}
                  <span className="font-semibold text-foreground">{formatDateTime(epgStats?.next_fetch_at)}</span>
                </p>
                <p>
                  Last updated channels:{" "}
                  <span className="font-semibold text-foreground">{epgStats?.last_updated_channels_count ?? "N/A"}</span>
                </p>
                <p>
                  Total sources:{" "}
                  <span className="font-semibold text-foreground">{epgStats?.sources_total ?? "N/A"}</span>
                </p>
              </div>
            </div>
          </div>
          {epgStats?.error && (
            <div className="status-danger w-full rounded-lg border p-4">
              <p className="text-sm">{epgStats.error}</p>
            </div>
          )}
        </SectionCard>

        <SectionCard
          className="xl:col-span-1"
          title={(
            <div className="flex items-center gap-2">
              <Badge variant={getHealthBadgeVariant(rutvStats?.health)}>
                {rutvStats?.health?.toUpperCase() ?? (isRutvLoading ? "LOADING" : "N/A")}
              </Badge>
              <span>RUTV Site</span>
            </div>
          )}
          bodyClassName="flex flex-col gap-4"
        >
          <div className="w-full rounded-xl border border-border bg-muted p-4">
            <div className="flex flex-col">
              <div className="space-y-2 text-sm text-muted-foreground">
                <p>
                  Unique visits:{" "}
                  <span className="font-semibold text-foreground">{rutvStats?.unique_visits ?? "N/A"}</span>
                </p>
                <p>
                  Contact forms:{" "}
                  <span className="font-semibold text-foreground">
                    {rutvStats?.successful_contact_forms ?? "N/A"}
                  </span>
                </p>
                <p>
                  Window start:{" "}
                  <span className="font-semibold text-foreground">{formatDateTime(rutvStats?.from_at)}</span>
                </p>
                <p>
                  Window end:{" "}
                  <span className="font-semibold text-foreground">{formatDateTime(rutvStats?.to_at)}</span>
                </p>
              </div>
            </div>
          </div>
          {rutvStats?.error && (
            <div className="status-danger w-full rounded-lg border p-4">
              <p className="text-sm">{rutvStats.error}</p>
            </div>
          )}
        </SectionCard>

        <SectionCard
          className="xl:col-span-1"
          title={(
            <div className="flex items-center gap-2">
              <Badge variant={getHealthBadgeVariant(flussonicStats?.health, flussonicStats?.error)}>
                {isNotConfigured(flussonicStats?.error)
                  ? "NOT CONFIGURED"
                  : flussonicStats?.health?.toUpperCase() ?? (isFlussonicLoading ? "LOADING" : "N/A")}
              </Badge>
              <span>Flussonic</span>
            </div>
          )}
          bodyClassName="flex flex-col gap-4"
          actions={
            <Button
              onClick={() => handleSync("flussonic")}
              loading={syncMutation.isPending}
              disabled={isNotConfigured(flussonicStats?.error)}
            >
              <svg className="mr-2 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Sync Now
            </Button>
          }
        >
          {isNotConfigured(flussonicStats?.error) ? (
            <div className="w-full rounded-xl border border-border bg-muted p-4">
              <p className="text-sm text-muted-foreground">Flussonic is not configured in the current environment.</p>
            </div>
          ) : (
            <div className="w-full rounded-xl border border-border bg-muted p-4">
              <div className="flex flex-col">
                <div className="space-y-2 text-sm text-muted-foreground">
                  <p>
                    Incoming:{" "}
                    <span className="font-semibold text-foreground">{formatTrafficKbit(flussonicStats?.incoming_kbit)}</span>
                  </p>
                  <p>
                    Outgoing:{" "}
                    <span className="font-semibold text-foreground">{formatTrafficKbit(flussonicStats?.outgoing_kbit)}</span>
                  </p>
                  <p>
                    Clients:{" "}
                    <span className="font-semibold text-foreground">{flussonicStats?.total_clients ?? "N/A"}</span>
                  </p>
                  <p>
                    Total sources:{" "}
                    <span className="font-semibold text-foreground">{flussonicStats?.total_sources ?? "N/A"}</span>
                  </p>
                  <p>
                    Good/Broken:{" "}
                    <span className="font-semibold text-foreground">
                      {flussonicStats?.good_sources ?? "N/A"} / {flussonicStats?.broken_sources ?? "N/A"}
                    </span>
                  </p>
                  <p>
                    Active online24:{" "}
                    <span className="font-semibold text-foreground">
                      {flussonicStats?.active_source_counters?.online24 ?? "N/A"}
                    </span>
                  </p>
                  <p>
                    Active restream.pw / 185.96.80.44:{" "}
                    <span className="font-semibold text-foreground">
                      {flussonicStats?.active_source_counters?.restream ?? "N/A"}
                    </span>
                  </p>
                  <p>
                    Active other:{" "}
                    <span className="font-semibold text-foreground">
                      {flussonicStats?.active_source_counters?.other ?? "N/A"}
                    </span>
                  </p>
                </div>
              </div>
            </div>
          )}
          {flussonicStats?.error && !isNotConfigured(flussonicStats.error) && (
            <div className="status-danger w-full rounded-lg border p-4">
              <p className="text-sm">{flussonicStats.error}</p>
            </div>
          )}
        </SectionCard>

        <SectionCard
          className="xl:col-span-1"
          title={(
            <div className="flex items-center gap-2">
              <Badge variant={getHealthBadgeVariant(nimbleStats?.health, nimbleStats?.error)}>
                {isNotConfigured(nimbleStats?.error)
                  ? "NOT CONFIGURED"
                  : nimbleStats?.health?.toUpperCase() ?? (isNimbleLoading ? "LOADING" : "N/A")}
              </Badge>
              <span>Nimble</span>
            </div>
          )}
          bodyClassName="flex flex-col gap-4"
          actions={
            <Button
              onClick={() => handleSync("nimble")}
              loading={syncMutation.isPending}
              disabled={isNotConfigured(nimbleStats?.error)}
            >
              <svg className="mr-2 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Sync Now
            </Button>
          }
        >
          {isNotConfigured(nimbleStats?.error) ? (
            <div className="w-full rounded-xl border border-border bg-muted p-4">
              <p className="text-sm text-muted-foreground">Nimble is not configured in the current environment.</p>
            </div>
          ) : (
            <div className="w-full rounded-xl border border-border bg-muted p-4">
              <div className="flex flex-col">
                <div className="space-y-2 text-sm text-muted-foreground">
                  <p>
                    Incoming:{" "}
                    <span className="font-semibold text-foreground">{formatTrafficKbit(nimbleStats?.incoming_kbit)}</span>
                  </p>
                  <p>
                    Outgoing:{" "}
                    <span className="font-semibold text-foreground">{formatTrafficKbit(nimbleStats?.outgoing_kbit)}</span>
                  </p>
                  <p>
                    Clients:{" "}
                    <span className="font-semibold text-foreground">{nimbleStats?.total_clients ?? "N/A"}</span>
                  </p>
                  <p>
                    Total sources:{" "}
                    <span className="font-semibold text-foreground">{nimbleStats?.total_sources ?? "N/A"}</span>
                  </p>
                  <p>
                    Good/Broken:{" "}
                    <span className="font-semibold text-foreground">
                      {nimbleStats?.good_sources ?? "N/A"} / {nimbleStats?.broken_sources ?? "N/A"}
                    </span>
                  </p>
                </div>
              </div>
            </div>
          )}
          {nimbleStats?.error && !isNotConfigured(nimbleStats.error) && (
            <div className="status-danger w-full rounded-lg border p-4">
              <p className="text-sm">{nimbleStats.error}</p>
            </div>
          )}
        </SectionCard>

        <SectionCard
          className="xl:col-span-1"
          title={(
            <div className="flex items-center gap-2">
              <Badge variant={getHealthBadgeVariant(authStats?.health)}>
                {authStats?.health?.toUpperCase() ?? (isAuthLoading ? "LOADING" : "N/A")}
              </Badge>
              <span>Auth Service</span>
            </div>
          )}
          bodyClassName="flex flex-col gap-4"
        >
          <div className="w-full rounded-xl border border-border bg-muted p-4">
            <div className="flex flex-col">
              <div className="space-y-2 text-sm text-muted-foreground">
                <p>
                  Active tokens:{" "}
                  <span className="font-semibold text-foreground">{authStats?.active_tokens ?? "N/A"}</span>
                </p>
                <p>
                  Active sessions:{" "}
                  <span className="font-semibold text-foreground">{authStats?.active_sessions ?? "N/A"}</span>
                </p>
              </div>
            </div>
          </div>
          {authStats?.error && (
            <div className="status-danger w-full rounded-lg border p-4">
              <p className="text-sm">{authStats.error}</p>
            </div>
          )}
        </SectionCard>
      </div>

      {syncMessage && (
        <div className="status-success rounded-lg border p-4">
          <p className="text-sm">{syncMessage}</p>
        </div>
      )}
    </div>
  );
}
