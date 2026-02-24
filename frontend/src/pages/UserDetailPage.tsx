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
import { Modal } from "../components/ui/Modal";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { Spinner } from "../components/ui/Spinner";
import { MultiSelect, type SelectOption } from "../components/ui/MultiSelect";
import { DatePicker } from "../components/ui/DatePicker";
import { SortableHeader } from "../components/table/SortableHeader";
import { buildPlaylistUrl } from "../utils/playlist";
import { formatDateTime, formatDuration, truncateText } from "../utils/formatters";
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
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/users" className="text-gray-500 hover:text-gray-700">&larr; Back to Users</Link>
          <h1 className="text-2xl font-bold text-gray-800">
            {isEdit ? `Edit User: ${user?.last_name} ${user?.first_name}` : "New User"}
          </h1>
        </div>
        {isEdit && (
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-600">Playlist URL:</span>
            <input
              type="text"
              readOnly
              value={playlistUrl}
              className="w-72 px-2 py-1 text-xs border border-gray-200 rounded bg-gray-50 text-gray-600"
            />
            <Button variant="secondary" onClick={() => setPreviewOpen(true)}>Preview Playlist</Button>
            <button
              onClick={downloadPlaylist}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 text-sm"
            >
              Download Playlist
            </button>
          </div>
        )}
      </div>

      <form onSubmit={onSubmit} className="bg-white rounded-lg shadow">
        {/* User Information */}
        <div className="px-6 py-4 border-b">
          <h2 className="text-lg font-semibold text-gray-800">User Information</h2>
        </div>
        <div className="px-6 py-4 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">First Name *</label>
              <input
                type="text"
                required
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Last Name *</label>
              <input
                type="text"
                required
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Agreement Number *</label>
              <input
                type="text"
                required
                value={agreementNumber}
                onChange={(e) => setAgreementNumber(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Max Sessions</label>
              <input
                type="number"
                min={1}
                value={maxSessions}
                onChange={(e) => setMaxSessions(Number(e.target.value) || 1)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <DatePicker label="Valid From" selected={validFrom} onChange={setValidFrom} />
            <DatePicker label="Valid Until" selected={validUntil} onChange={setValidUntil} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Status</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="enabled">Enabled</option>
              <option value="disabled">Disabled</option>
            </select>
          </div>
          {isEdit && user && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700">Token</label>
                <div className="mt-1 flex items-center space-x-2">
                  <input type="text" readOnly value={user.token} className="block w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-gray-600 text-sm font-mono" />
                  <button
                    type="button"
                    onClick={() => setRegenOpen(true)}
                    className="px-3 py-2 border border-orange-300 text-orange-700 rounded-md hover:bg-orange-50 text-sm whitespace-nowrap"
                  >
                    Regenerate
                  </button>
                </div>
              </div>
              <div className="flex items-center space-x-3 pt-2">
                <button type="button" onClick={() => setSessionsOpen(true)} className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 text-sm">
                  Sessions Log
                </button>
                <button type="button" onClick={() => setAccessOpen(true)} className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 text-sm">
                  Access Log
                </button>
              </div>
            </>
          )}
        </div>

        {/* Channel Assignment */}
        <div className="px-6 py-4 border-t border-b">
          <h2 className="text-lg font-semibold text-gray-800">Channel Assignment</h2>
        </div>
        <div className="px-6 py-4 space-y-4">
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
            <div className="flex items-center justify-between pt-4 border-t">
              <span className="text-sm text-gray-600">
                Resolved Channels: <strong>{resolvedChannels.length}</strong> total
              </span>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="px-6 py-4 border-t bg-gray-50 flex justify-end space-x-3">
          <Link to="/users" className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-100">
            Cancel
          </Link>
          {isEdit && (
            <button type="button" onClick={() => setDeleteOpen(true)} className="px-4 py-2 border border-red-300 text-red-700 rounded-md hover:bg-red-50">
              Delete
            </button>
          )}
          <Button type="submit" loading={createUser.isPending || updateUser.isPending}>Save</Button>
        </div>
      </form>

      {/* Delete Confirmation */}
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

      {/* Regenerate Token Confirmation */}
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

      {/* Playlist Preview Modal */}
      {previewOpen && (
        <Modal
          open={previewOpen}
          onClose={() => setPreviewOpen(false)}
          title="Playlist Preview"
          maxWidth="max-w-4xl"
          footer={<Button variant="secondary" onClick={() => setPreviewOpen(false)}>Close</Button>}
        >
          {playlist ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Filename: <strong>{playlist.filename}</strong></span>
                <span className="text-sm text-gray-600">Channels: <strong>{playlist.channel_count}</strong></span>
              </div>
              <textarea
                readOnly
                rows={15}
                value={playlist.content}
                className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 font-mono text-xs"
              />
            </div>
          ) : (
            <div className="flex justify-center py-8"><Spinner /></div>
          )}
        </Modal>
      )}

      {/* Sessions Log Modal */}
      {sessionsOpen && (
        <Modal
          open={sessionsOpen}
          onClose={() => setSessionsOpen(false)}
          title="Sessions Log"
          maxWidth="max-w-6xl"
        >
          <div className="space-y-4">
            <div className="flex items-center space-x-4">
              <div>
                <label className="block text-xs text-gray-500 mb-1">From</label>
                <input
                  type="date"
                  value={sessionsFrom}
                  onChange={(e) => setSessionsFrom(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-md text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">To</label>
                <input
                  type="date"
                  value={sessionsTo}
                  onChange={(e) => setSessionsTo(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-md text-sm"
                />
              </div>
            </div>
            <div className="max-h-[60vh] overflow-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      <SortableHeader label="Started" field="started_at" sortBy={sessionSort.sortBy} sortDir={sessionSort.sortDir} onSort={sessionSort.toggleSort} />
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      <SortableHeader label="Ended" field="ended_at" sortBy={sessionSort.sortBy} sortDir={sessionSort.sortDir} onSort={sessionSort.toggleSort} />
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      <SortableHeader label="Duration" field="duration" sortBy={sessionSort.sortBy} sortDir={sessionSort.sortDir} onSort={sessionSort.toggleSort} />
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      <SortableHeader label="IP Address" field="ip" sortBy={sessionSort.sortBy} sortDir={sessionSort.sortDir} onSort={sessionSort.toggleSort} />
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      <SortableHeader label="Channel" field="channel" sortBy={sessionSort.sortBy} sortDir={sessionSort.sortDir} onSort={sessionSort.toggleSort} />
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Protocol</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {sortedSessions.length === 0 ? (
                    <tr><td colSpan={6} className="py-8 text-center text-gray-500">No sessions found for this period</td></tr>
                  ) : (
                    sortedSessions.map((s, i) => (
                      <tr key={i}>
                        <td className="px-3 py-2 text-sm">{formatDateTime(s.started_at)}</td>
                        <td className="px-3 py-2 text-sm">{s.ended_at ? formatDateTime(s.ended_at) : <span className="text-green-600">Active</span>}</td>
                        <td className="px-3 py-2 text-sm">{formatDuration(s.duration)}</td>
                        <td className="px-3 py-2 text-sm font-mono">{s.ip || "-"}</td>
                        <td className="px-3 py-2 text-sm">{s.channel || "-"}</td>
                        <td className="px-3 py-2 text-sm text-gray-500 truncate max-w-xs" title={s.user_agent || ""}>{truncateText(s.user_agent || "", 40) || "-"}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            {sessions && sessions.pages > 1 && (
              <div className="text-sm text-gray-600">Total: {sessions.total} records</div>
            )}
          </div>
        </Modal>
      )}

      {/* Access Log Modal */}
      {accessOpen && (
        <Modal
          open={accessOpen}
          onClose={() => setAccessOpen(false)}
          title="Access Log"
          maxWidth="max-w-6xl"
        >
          <div className="space-y-4">
            <div className="flex items-center space-x-4">
              <div>
                <label className="block text-xs text-gray-500 mb-1">From</label>
                <input
                  type="date"
                  value={accessFrom}
                  onChange={(e) => setAccessFrom(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-md text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">To</label>
                <input
                  type="date"
                  value={accessTo}
                  onChange={(e) => setAccessTo(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-md text-sm"
                />
              </div>
            </div>
            <div className="max-h-[60vh] overflow-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      <SortableHeader label="Timestamp" field="accessed_at" sortBy={accessSort.sortBy} sortDir={accessSort.sortDir} onSort={accessSort.toggleSort} />
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      <SortableHeader label="IP Address" field="ip" sortBy={accessSort.sortBy} sortDir={accessSort.sortDir} onSort={accessSort.toggleSort} />
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      <SortableHeader label="Channel" field="channel" sortBy={accessSort.sortBy} sortDir={accessSort.sortDir} onSort={accessSort.toggleSort} />
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      <SortableHeader label="Action" field="action" sortBy={accessSort.sortBy} sortDir={accessSort.sortDir} onSort={accessSort.toggleSort} />
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Protocol</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {sortedAccess.length === 0 ? (
                    <tr><td colSpan={5} className="py-8 text-center text-gray-500">No access logs found for this period</td></tr>
                  ) : (
                    sortedAccess.map((log, i) => (
                      <tr key={i}>
                        <td className="px-3 py-2 text-sm">{formatDateTime(log.accessed_at)}</td>
                        <td className="px-3 py-2 text-sm font-mono">{log.ip || "-"}</td>
                        <td className="px-3 py-2 text-sm">{log.channel || "-"}</td>
                        <td className="px-3 py-2 text-sm">{log.action || "-"}</td>
                        <td className="px-3 py-2 text-sm text-gray-500 truncate max-w-xs" title={log.user_agent || ""}>{truncateText(log.user_agent || "", 40) || "-"}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            {accessLogs && accessLogs.pages > 1 && (
              <div className="text-sm text-gray-600">Total: {accessLogs.total} records</div>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
}
