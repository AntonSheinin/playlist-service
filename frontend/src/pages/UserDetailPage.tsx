import { useState, useEffect, useMemo, useCallback, type FormEvent } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import type { MultiValue } from "react-select";
import {
  useUser,
  useCreateUser,
  useUpdateUser,
  useDeleteUser,
  useRegenerateToken,
  useResolvedChannels,
  usePlaylistPreview,
  useUserSessions,
  useUserAccessLogs,
} from "../hooks/useUsers";
import { useLookupTariffs, useLookupPackages, useLookupChannels } from "../hooks/useLookup";
import { useToast } from "../hooks/useToast";
import { useSortable } from "../hooks/useSortable";
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
import {
  AccessLogModal,
  PlaylistPreviewModal,
  SessionsLogModal,
} from "../components/users/UserDetailModals";
import { buildPlaylistUrl } from "../utils/playlist";
import type { UserCreate, UserUpdate } from "../api/types";

function toDateStr(d: Date): string {
  return d.toISOString().split("T")[0];
}

function todayStr(): string {
  return toDateStr(new Date());
}

function sevenDaysAgoStr(): string {
  const d = new Date();
  d.setDate(d.getDate() - 7);
  return toDateStr(d);
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
  const { data: resolvedChannels } = useResolvedChannels(userId);

  // Lookups
  const { data: lookupTariffs } = useLookupTariffs();
  const { data: lookupPackages } = useLookupPackages();
  const { data: lookupChannels } = useLookupChannels();

  // Form fields (plain useState instead of react-hook-form)
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [agreementNumber, setAgreementNumber] = useState("");
  const [maxSessions, setMaxSessions] = useState(1);
  const [status, setStatus] = useState("enabled");

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
        label: c.display_name || c.tvg_name || c.stream_name || `Channel ${c.id}`,
      })),
    [lookupChannels]
  );

  // Populate form when user data loads
  useEffect(() => {
    if (!user) return;
    setFirstName(user.first_name);
    setLastName(user.last_name);
    setAgreementNumber(user.agreement_number);
    setMaxSessions(user.max_sessions);
    setStatus(user.status);
    setValidFrom(user.valid_from ? new Date(user.valid_from) : null);
    setValidUntil(user.valid_until ? new Date(user.valid_until) : null);
    setSelectedTariffs(user.tariffs.map((t) => ({ value: t.id, label: t.name })));
    setSelectedPackages(user.packages.map((p) => ({ value: p.id, label: p.name })));
    setSelectedChannels(
      user.channels.map((c) => ({
        value: c.id,
        label: c.display_name || c.tvg_name || c.stream_name || `Channel ${c.id}`,
      }))
    );
  }, [user]);

  // Playlist URL (live update)
  const playlistUrl = buildPlaylistUrl(firstName, lastName, agreementNumber);

  const onSubmit = useCallback(async (e: FormEvent) => {
    e.preventDefault();
    const base = {
      first_name: firstName,
      last_name: lastName,
      agreement_number: agreementNumber,
      max_sessions: maxSessions,
      status: status as "enabled" | "disabled",
      tariff_ids: selectedTariffs.map((t) => t.value),
      package_ids: selectedPackages.map((p) => p.value),
      channel_ids: selectedChannels.map((c) => c.value),
    };

    try {
      if (isEdit) {
        const payload: UserUpdate = {
          ...base,
          clear_valid_from: !validFrom,
          clear_valid_until: !validUntil,
        };
        if (validFrom) payload.valid_from = toDateStr(validFrom) + "T00:00:00";
        if (validUntil) payload.valid_until = toDateStr(validUntil) + "T23:59:59";

        await updateUser.mutateAsync({ id: userId!, data: payload });
        showToast("User updated", "success");
      } else {
        const payload: UserCreate = { ...base };
        if (validFrom) payload.valid_from = toDateStr(validFrom) + "T00:00:00";
        if (validUntil) payload.valid_until = toDateStr(validUntil) + "T23:59:59";

        const newUser = await createUser.mutateAsync(payload);
        showToast("User created", "success");
        navigate(`/users/${newUser.id}`, { replace: true });
      }
    } catch {
      showToast("Failed to save user", "error");
    }
  }, [firstName, lastName, agreementNumber, maxSessions, status, selectedTariffs, selectedPackages, selectedChannels, validFrom, validUntil, isEdit, userId, updateUser, createUser, showToast, navigate]);

  async function handleRegenToken() {
    if (!userId) return;
    try {
      await regenToken.mutateAsync(userId);
      showToast("Token regenerated", "success");
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
    } catch {
      showToast("Failed to delete user", "error");
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
          {isEdit && user && (
            <>
              <div>
                <div className="mt-1 flex items-end gap-2">
                  <Input
                    label="Token"
                    type="text"
                    readOnly
                    value={user.token}
                    className="bg-slate-50 font-mono text-sm text-slate-600"
                  />
                  <Button
                    type="button"
                    onClick={() => setRegenOpen(true)}
                    variant="secondary"
                    className="whitespace-nowrap border-amber-300 text-amber-700 hover:bg-amber-50"
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
            onChange={(v: MultiValue<SelectOption>) => setSelectedTariffs([...v])}
          />
          <MultiSelect
            label="Additional Packages (beyond tariffs)"
            options={packageOptions}
            value={selectedPackages}
            onChange={(v: MultiValue<SelectOption>) => setSelectedPackages([...v])}
          />
          <MultiSelect
            label="Additional Channels (individual)"
            options={channelOptions}
            value={selectedChannels}
            onChange={(v: MultiValue<SelectOption>) => setSelectedChannels([...v])}
          />
          {isEdit && resolvedChannels && (
            <div className="flex items-center justify-between border-t border-slate-200 pt-4">
              <span className="text-sm text-slate-600">
                Resolved Channels: <strong>{resolvedChannels.length}</strong> total
              </span>
            </div>
          )}
        </SectionCard>

        <Card className="border border-slate-200 bg-slate-50 p-4">
          <div className="flex flex-wrap justify-end gap-3">
            <Link to="/users">
              <Button type="button" variant="secondary">Cancel</Button>
            </Link>
          {isEdit && (
              <Button type="button" variant="danger" onClick={() => setDeleteOpen(true)}>
                Delete
              </Button>
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
