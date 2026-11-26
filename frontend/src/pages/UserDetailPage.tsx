import { useState, useEffect, useMemo, useCallback, useRef, type FormEvent } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import {
  useUser,
  useCreateUser,
  useUpdateUser,
  useDeleteUser,
  useRegenerateToken,
  useSyncUser,
  useResolvedChannels,
  usePlaylistPreview,
  useUserSessions,
  useUserAccessLogs,
} from "../hooks/useUsers";
import { useLookupTariffs, useLookupPackages, useLookupChannels } from "../hooks/useLookup";
import { useToast } from "../hooks/useToast";
import { useSortable } from "../hooks/useSortable";
import { useDebounce } from "../hooks/useDebounce";
import { Button } from "../components/ui/Button";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { Spinner } from "../components/ui/Spinner";
import { MultiSelect, type SelectOption } from "../components/ui/MultiSelect";
import { DatePicker } from "../components/ui/DatePicker";
import { Input } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { Card } from "../components/ui/Card";
import { SectionCard } from "../components/ui/SectionCard";
import { UserDetailHeader } from "../components/users/UserDetailHeader";
import { AccountSyncBadges } from "../components/users/AccountSyncBadges";
import {
  AccessLogModal,
  PlaylistPreviewModal,
  SessionsLogModal,
} from "../components/users/UserDetailModals";
import { ApiError } from "../api/client";
import type { UserSaveResponse } from "../api/types";
import { buildPlaylistUrl } from "../utils/playlist";
import { buildUserUpdate } from "../utils/userForm";
import { formatDate, parseLocalDate } from "../utils/formatters";
import { formatChannelOptionLabel } from "../utils/channels";

function syncFailureMessage(user: UserSaveResponse): string {
  const failed = [];
  if (user.auth_sync_result === "failed") failed.push("Auth");
  if (user.portal_sync_result === "failed") failed.push("Portal");
  return failed.length ? ` ${failed.join(" and ")} sync failed.` : "";
}

function todayStr(): string {
  return formatDate(new Date());
}

function sevenDaysAgoStr(): string {
  const d = new Date();
  d.setDate(d.getDate() - 7);
  return formatDate(d);
}

export function UserDetailPage() {
  const { userId: paramId } = useParams<{ userId: string }>();
  const userId = paramId ? Number(paramId) : undefined;
  const isEdit = !!userId;
  const navigate = useNavigate();
  const { showToast } = useToast();

  const { data: user, isLoading } = useUser(userId);
  const createUser = useCreateUser();
  const updateUser = useUpdateUser();
  const deleteUserMut = useDeleteUser();
  const regenToken = useRegenerateToken();
  const syncAuth = useSyncUser("auth");
  const syncPortal = useSyncUser("portal");
  const portalSyncAvailable = user?.portal_sync_available ?? false;
  const { data: resolvedChannels } = useResolvedChannels(userId);

  // Lookups
  const { data: lookupTariffs } = useLookupTariffs();
  const { data: lookupPackages } = useLookupPackages();
  const [channelSearchInput, setChannelSearchInput] = useState("");
  const channelSearch = useDebounce(channelSearchInput);
  const { data: lookupChannels, isLoading: lookupChannelsLoading } = useLookupChannels(channelSearch);

  // Form fields (plain useState instead of react-hook-form)
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [agreementNumber, setAgreementNumber] = useState("");
  const [playlistName, setPlaylistName] = useState("");
  const [playlistNameError, setPlaylistNameError] = useState("");
  const [maxSessions, setMaxSessions] = useState(1);
  const [status, setStatus] = useState("enabled");
  const [portalAllowed, setPortalAllowed] = useState(false);
  const [maxPortalDevices, setMaxPortalDevices] = useState("1");
  const portalSettingsChanged = !!user && (
    portalAllowed !== user.portal_allowed ||
    (portalAllowed && Number(maxPortalDevices) !== user.max_portal_devices)
  );

  // Multi-selects
  const [selectedTariffs, setSelectedTariffs] = useState<SelectOption[]>([]);
  const [selectedPackages, setSelectedPackages] = useState<SelectOption[]>([]);
  const [selectedChannels, setSelectedChannels] = useState<SelectOption[]>([]);

  // Dates
  const [validFrom, setValidFrom] = useState<Date | null>(null);
  const [validUntil, setValidUntil] = useState<Date | null>(null);

  // Modals
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [regenOpen, setRegenOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [sessionsOpen, setSessionsOpen] = useState(false);
  const [accessOpen, setAccessOpen] = useState(false);

  // Sessions/Access log filters
  const [sessionsFrom, setSessionsFrom] = useState(sevenDaysAgoStr);
  const [sessionsTo, setSessionsTo] = useState(todayStr);
  const [accessFrom, setAccessFrom] = useState(sevenDaysAgoStr);
  const [accessTo, setAccessTo] = useState(todayStr);
  const sessionSort = useSortable("started_at", "desc");
  const accessSort = useSortable("accessed_at", "desc");

  // Sessions/Access log params
  const today = useMemo(() => todayStr(), []);
  const sessionsParams = useMemo(() => {
    const p: { from_date?: string; to_date?: string } = {};
    if (sessionsFrom) p.from_date = `${sessionsFrom}T00:00:00`;
    if (sessionsTo && sessionsTo !== today) p.to_date = `${sessionsTo}T23:59:59`;
    return p;
  }, [sessionsFrom, sessionsTo, today]);

  const accessParams = useMemo(() => {
    const p: { from_date?: string; to_date?: string } = {};
    if (accessFrom) p.from_date = `${accessFrom}T00:00:00`;
    if (accessTo && accessTo !== today) p.to_date = `${accessTo}T23:59:59`;
    return p;
  }, [accessFrom, accessTo, today]);

  const { data: sessions } = useUserSessions(sessionsOpen ? userId : undefined, sessionsParams);
  const { data: accessLogs } = useUserAccessLogs(accessOpen ? userId : undefined, accessParams);
  const { data: playlist } = usePlaylistPreview(previewOpen ? userId : undefined);

  // Lookup options
  const tariffOptions = useMemo(
    () => (lookupTariffs || []).map((t) => ({ value: t.id, label: t.name })),
    [lookupTariffs]
  );
  const packageOptions = useMemo(
    () => (lookupPackages || []).map((p) => ({ value: p.id, label: p.name })),
    [lookupPackages]
  );
  const channelOptions = useMemo(
    () =>
      (lookupChannels || []).map((c) => ({
        value: c.id,
        label: formatChannelOptionLabel(c),
      })),
    [lookupChannels]
  );

  const loadedForm = useRef("");
  // Sync status refreshes should preserve unsaved edits.
  useEffect(() => {
    if (!user) return;
    const savedForm = JSON.stringify([
      user.id, user.first_name, user.last_name, user.agreement_number, user.playlist_name,
      user.max_sessions, user.status, user.portal_allowed, user.max_portal_devices,
      user.valid_from, user.valid_until,
      user.tariffs, user.packages, user.channels,
    ]);
    if (loadedForm.current === savedForm) return;
    const timeout = window.setTimeout(() => {
      loadedForm.current = savedForm;
      setFirstName(user.first_name);
      setLastName(user.last_name);
      setAgreementNumber(user.agreement_number);
      setPlaylistName(user.playlist_name);
      setPlaylistNameError("");
      setMaxSessions(user.max_sessions);
      setStatus(user.status);
      setPortalAllowed(user.portal_allowed);
      setMaxPortalDevices(String(user.max_portal_devices));
      setValidFrom(parseLocalDate(user.valid_from));
      setValidUntil(parseLocalDate(user.valid_until));
      setSelectedTariffs(user.tariffs.map((t) => ({ value: t.id, label: t.name })));
      setSelectedPackages(user.packages.map((p) => ({ value: p.id, label: p.name })));
      setSelectedChannels(
        user.channels.map((c) => ({
          value: c.id,
          label: formatChannelOptionLabel(c),
        }))
      );
    }, 0);
    return () => window.clearTimeout(timeout);
  }, [user]);

  const playlistUrl = user ? buildPlaylistUrl(user.playlist_name) : "";

  const onSubmit = useCallback(async (e: FormEvent) => {
    e.preventDefault();
    setPlaylistNameError("");
    const playlistNameLength = Array.from(playlistName).length;
    if (isEdit && (
      playlistNameLength < 1 || playlistNameLength > 302 || !/^[\p{L}\p{N}_-]+$/u.test(playlistName)
    )) {
      setPlaylistNameError("Use 1 to 302 letters, numbers, underscores, or hyphens; omit .m3u8.");
      return;
    }
    const base = {
      first_name: firstName,
      last_name: lastName,
      agreement_number: agreementNumber,
      max_sessions: maxSessions,
      status: status as "enabled" | "disabled",
      portal_allowed: portalAllowed,
      ...(portalAllowed ? { max_portal_devices: Number(maxPortalDevices) } : {}),
      tariff_ids: selectedTariffs.map((t) => t.value),
      package_ids: selectedPackages.map((p) => p.value),
      channel_ids: selectedChannels.map((c) => c.value),
      valid_from: validFrom ? formatDate(validFrom) + "T00:00:00" : null,
      valid_until: validUntil ? formatDate(validUntil) + "T23:59:59" : null,
    };

    try {
      if (isEdit) {
        if (!user) return;
        const payload = buildUserUpdate(user, { ...base, playlist_name: playlistName });
        const saved = await updateUser.mutateAsync({ id: userId!, data: payload });
        const warning = syncFailureMessage(saved);
        showToast(warning ? `Account saved.${warning}` : "User updated", warning ? "warning" : "success");
      } else {
        const newUser = await createUser.mutateAsync(base);
        const warning = syncFailureMessage(newUser);
        showToast(warning ? `Account created.${warning}` : "User created", warning ? "warning" : "success");
        navigate(`/users/${newUser.id}`, { replace: true });
      }
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Failed to save user";
      if (
        isEdit && error instanceof ApiError && error.code === "DUPLICATE_ENTRY"
        && message.includes("Playlist URL name")
      ) {
        setPlaylistNameError(message);
      }
      showToast(message, "error");
    }
  }, [firstName, lastName, agreementNumber, playlistName, maxSessions, status, portalAllowed, maxPortalDevices, selectedTariffs, selectedPackages, selectedChannels, validFrom, validUntil, isEdit, userId, user, updateUser, createUser, showToast, navigate]);

  async function handleSync(service: "auth" | "portal") {
    if (!userId) return;
    const mutation = service === "auth" ? syncAuth : syncPortal;
    const name = service === "auth" ? "Auth" : "Portal";
    try {
      await mutation.mutateAsync(userId);
      showToast(`${name} synced`, "success");
    } catch (error) {
      const detail = error instanceof ApiError ? ` ${error.message}` : "";
      showToast(`${name} sync failed.${detail}`, "error");
    }
  }

  async function handleRegenToken() {
    if (!userId) return;
    try {
      const saved = await regenToken.mutateAsync(userId);
      const warning = syncFailureMessage(saved);
      showToast(warning ? `Token regenerated.${warning}` : "Token regenerated", warning ? "warning" : "success");
      setRegenOpen(false);
    } catch {
      showToast("Failed to regenerate token", "error");
    }
  }

  async function handleDelete() {
    if (!userId) return;
    try {
      await deleteUserMut.mutateAsync(userId);
      showToast("User deleted", "success");
      navigate("/users", { replace: true });
    } catch (error) {
      showToast(error instanceof ApiError ? error.message : "Failed to delete user", "error");
    }
  }

  function downloadPlaylist() {
    if (playlistUrl) {
      window.open(playlistUrl, "_blank");
    }
  }

  // Sorted sessions data
  const sortedSessions = useMemo(() => {
    const items = sessions?.items || [];
    return [...items].sort((a, b) => {
      const dir = sessionSort.sortDir === "asc" ? 1 : -1;
      switch (sessionSort.sortBy) {
        case "started_at": return dir * ((a.started_at || "").localeCompare(b.started_at || ""));
        case "ended_at": return dir * ((a.ended_at || "").localeCompare(b.ended_at || ""));
        case "duration": return dir * ((a.duration || 0) - (b.duration || 0));
        case "ip": return dir * ((a.ip || "").localeCompare(b.ip || ""));
        case "channel": return dir * ((a.channel || "").localeCompare(b.channel || ""));
        default: return 0;
      }
    });
  }, [sessions, sessionSort.sortBy, sessionSort.sortDir]);

  // Sorted access log data
  const sortedAccess = useMemo(() => {
    const items = accessLogs?.items || [];
    return [...items].sort((a, b) => {
      const dir = accessSort.sortDir === "asc" ? 1 : -1;
      switch (accessSort.sortBy) {
        case "accessed_at": return dir * ((a.accessed_at || "").localeCompare(b.accessed_at || ""));
        case "ip": return dir * ((a.ip || "").localeCompare(b.ip || ""));
        case "channel": return dir * ((a.channel || "").localeCompare(b.channel || ""));
        case "action": return dir * ((a.action || "").localeCompare(b.action || ""));
        default: return 0;
      }
    });
  }, [accessLogs, accessSort.sortBy, accessSort.sortDir]);

  if (isEdit && isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <UserDetailHeader
        isEdit={isEdit}
        userName={user ? `${user.last_name} ${user.first_name}` : undefined}
        playlistUrl={playlistUrl}
        onOpenPreview={() => setPreviewOpen(true)}
        onDownloadPlaylist={downloadPlaylist}
      />

      <form onSubmit={onSubmit} className="space-y-6">
        {isEdit && (
          <SectionCard title="Playlist" bodyClassName="space-y-2">
            <div className="flex items-end gap-2">
              <div className="flex-1">
                <Input
                  label="Playlist URL name"
                  required
                  value={playlistName}
                  onChange={(e) => {
                    setPlaylistName(e.target.value);
                    setPlaylistNameError("");
                  }}
                  error={playlistNameError}
                />
              </div>
              <span className="pb-2 text-sm text-muted-foreground">.m3u8</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Changing this name replaces the playlist URL. Update configured players after saving.
              Use 1 to 302 letters, numbers, underscores, or hyphens, without .m3u8.
            </p>
          </SectionCard>
        )}
        <SectionCard title="User Information" bodyClassName="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="First Name *"
              type="text"
              required
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
            />
            <Input
              label="Last Name *"
              type="text"
              required
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Agreement Number *"
              type="text"
              required
              value={agreementNumber}
              onChange={(e) => setAgreementNumber(e.target.value)}
            />
            <Input
              label="Max Sessions"
              type="number"
              min={1}
              value={maxSessions}
              onChange={(e) => setMaxSessions(Number(e.target.value) || 1)}
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <DatePicker label="Valid From" selected={validFrom} onChange={setValidFrom} />
            <DatePicker label="Valid Until" selected={validUntil} onChange={setValidUntil} />
          </div>
          <Select value={status} onChange={(e) => setStatus(e.target.value)} label="Status">
            <option value="enabled">Enabled</option>
            <option value="disabled">Disabled</option>
          </Select>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={portalAllowed}
              onChange={(e) => setPortalAllowed(e.target.checked)}
              className="h-4 w-4 accent-primary"
            />
            Allow portal access
          </label>
          <Input
            label="Max Portal Devices"
            type="number"
            min={1}
            max={2_147_483_647}
            required={portalAllowed}
            disabled={!portalAllowed}
            value={maxPortalDevices}
            onChange={(e) => setMaxPortalDevices(e.target.value)}
          />
          {isEdit && user && (
            <>
              <div>
                <div className="mt-1 flex items-end gap-2">
                  <Input
                    label="Token"
                    type="text"
                    readOnly
                    value={user.token}
                    className="bg-muted font-mono text-sm text-muted-foreground"
                  />
                  <Button
                    type="button"
                    onClick={() => setRegenOpen(true)}
                    variant="secondary"
                    className="whitespace-nowrap border-[var(--status-warning-border)] text-[var(--status-warning-text)] hover:bg-[var(--status-warning-bg)]"
                  >
                    Regenerate
                  </Button>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-3 pt-2">
                <Button type="button" variant="secondary" onClick={() => setSessionsOpen(true)}>
                  Sessions Log
                </Button>
                <Button type="button" variant="secondary" onClick={() => setAccessOpen(true)}>
                  Access Log
                </Button>
              </div>
            </>
          )}
        </SectionCard>

        <SectionCard title="Channel Assignment" bodyClassName="space-y-4">
          <MultiSelect
            label="Tariffs"
            options={tariffOptions}
            value={selectedTariffs}
            onChange={(v) => setSelectedTariffs([...v])}
          />
          <MultiSelect
            label="Additional Packages (beyond tariffs)"
            options={packageOptions}
            value={selectedPackages}
            onChange={(v) => setSelectedPackages([...v])}
          />
          <MultiSelect
            label="Additional Channels (individual)"
            options={channelOptions}
            value={selectedChannels}
            onChange={(v) => setSelectedChannels([...v])}
            onInputChange={setChannelSearchInput}
            isLoading={lookupChannelsLoading}
            placeholder="Type to search channels..."
            noOptionsMessage={(inputValue) =>
              inputValue ? "No channels found" : "Type to search channels"
            }
          />
          {isEdit && resolvedChannels && (
            <div className="flex items-center justify-between border-t border-border pt-4">
              <span className="text-sm text-muted-foreground">
                Resolved Channels: <strong>{resolvedChannels.length}</strong> total
              </span>
            </div>
          )}
        </SectionCard>

        <Card className="border border-border bg-muted p-4">
          {user && (
            <div className="mb-3 flex flex-wrap items-center gap-3">
              <AccountSyncBadges
                authSynced={user.auth_synced}
                portalSyncAvailable={user.portal_sync_available}
                portalSynced={user.portal_synced}
              />
              {portalSettingsChanged && (
                <span className="text-xs text-muted-foreground">Save Portal changes before syncing.</span>
              )}
              {user.portal_allowed && !portalSyncAvailable && !portalSettingsChanged && (
                <span className="text-xs text-muted-foreground">Portal sync is unavailable.</span>
              )}
            </div>
          )}
          <div className="flex flex-wrap justify-end gap-3">
            <Link to="/users">
              <Button type="button" variant="secondary">Cancel</Button>
            </Link>
          {isEdit && (
              <Button type="button" variant="danger" onClick={() => setDeleteOpen(true)}>
                Delete
              </Button>
          )}
            {user && (
              <>
                <Button
                  variant="secondary"
                  disabled={user.auth_synced || updateUser.isPending}
                  loading={syncAuth.isPending}
                  onClick={() => handleSync("auth")}
                >
                  Sync Auth
                </Button>
                {portalSyncAvailable && (
                  <Button
                    variant="secondary"
                    disabled={
                      portalSettingsChanged || updateUser.isPending
                    }
                    loading={syncPortal.isPending}
                    onClick={() => handleSync("portal")}
                  >
                    Sync Portal
                  </Button>
                )}
              </>
            )}
            <Button type="submit" loading={createUser.isPending || updateUser.isPending}>
              Save
            </Button>
          </div>
        </Card>
      </form>

      {deleteOpen && (
        <ConfirmDialog
          open={deleteOpen}
          onClose={() => setDeleteOpen(false)}
          onConfirm={handleDelete}
          title="Delete User"
          message="Are you sure you want to delete this user?"
          details="This action cannot be undone. The user will be removed from the Auth Service."
          loading={deleteUserMut.isPending}
        />
      )}

      {regenOpen && (
        <ConfirmDialog
          open={regenOpen}
          onClose={() => setRegenOpen(false)}
          onConfirm={handleRegenToken}
          title="Regenerate Token"
          message="Are you sure you want to regenerate the token?"
          details="The old token will no longer work. The user will need a new playlist."
          confirmLabel="Regenerate"
          loading={regenToken.isPending}
        />
      )}

      <PlaylistPreviewModal
        open={previewOpen}
        onClose={() => setPreviewOpen(false)}
        playlist={playlist}
      />

      <SessionsLogModal
        open={sessionsOpen}
        onClose={() => setSessionsOpen(false)}
        from={sessionsFrom}
        to={sessionsTo}
        onFromChange={setSessionsFrom}
        onToChange={setSessionsTo}
        sortedSessions={sortedSessions}
        sessions={sessions}
        sort={sessionSort}
      />

      <AccessLogModal
        open={accessOpen}
        onClose={() => setAccessOpen(false)}
        from={accessFrom}
        to={accessTo}
        onFromChange={setAccessFrom}
        onToChange={setAccessTo}
        sortedAccess={sortedAccess}
        accessLogs={accessLogs}
        sort={accessSort}
      />
    </div>
  );
}
